"""5.5: aceptar la invitación (D6). El mismo 404 uniforme para cualquier
rechazo, 401 antes del cuerpo, 422 con sesión válida y cuerpo roto, y dos
aceptaciones a la vez dejan un solo vínculo.

Escenarios de `gestion-de-usuarios`: Aceptación correcta; Email no
verificado; Autenticación antes del cuerpo; Cuerpo inválido con sesión
válida; Email principal en mayúsculas; Otro email; Token reusado o
vencido; Dos aceptaciones a la vez. Lecciones: L-016, L-017, L-020.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text

from proptech_core.acceso.dominio.sobres import generar
from proptech_core.compartido.base_de_datos import abrir_sesion

from ._api_edificios import ApiEdificio
from ._clerk import clerk_falso as clerk_falso
from ._clerk import encabezados, sub_de
from ._usuarios import preparar

pytestmark = pytest.mark.integracion

EMAIL = "invitada@example.invalid"


def _conteos(api_edificio: ApiEdificio) -> Any:
    return api_edificio.filas(
        "SELECT (SELECT count(*) FROM persona),(SELECT count(*) FROM invitacion),"
        "(SELECT count(*) FROM auditoria)"
    )


def _crear_invitacion(
    api_edificio: ApiEdificio,
    *,
    email: str = EMAIL,
    estado: str = "enviada",
    vence_el_sobre: datetime | None = None,
    vence_la_fila: datetime | None = None,
    clerk_usuario_id_previo: str | None = None,
) -> dict[str, Any]:
    ahora = datetime.now(UTC)
    vence_el_sobre = vence_el_sobre or ahora + timedelta(days=7)
    vence_la_fila = vence_la_fila or vence_el_sobre
    clave = api_edificio.app.state.configuracion.clave_para_invitar()
    resumen, sobre = generar(clave, vence_el_sobre)
    persona_id, invitacion_id = uuid4(), uuid4()
    with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, api_edificio.admin) as sesion:
        sesion.execute(
            text(
                "INSERT INTO persona (id, administracion_id, nombre, email, clerk_usuario_id) "
                "VALUES (:id, :admin, 'Invitada ficticia', :email, :clerk_id)"
            ),
            {
                "id": persona_id,
                "admin": api_edificio.admin,
                "email": email,
                "clerk_id": clerk_usuario_id_previo,
            },
        )
        sesion.execute(
            text(
                "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
                "VALUES (:admin, :persona, 'auxiliar', :edificio)"
            ),
            {"admin": api_edificio.admin, "persona": persona_id, "edificio": api_edificio.edificio},
        )
        sesion.execute(
            text(
                "INSERT INTO invitacion (id, administracion_id, persona_id, estado, "
                "token_resumen, vence, creada_por) VALUES "
                "(:id, :admin, :persona, :estado, :resumen, :vence, :persona)"
            ),
            {
                "id": invitacion_id,
                "admin": api_edificio.admin,
                "persona": persona_id,
                "estado": estado,
                "resumen": resumen,
                "vence": vence_la_fila,
            },
        )
        sesion.commit()
    return {"persona_id": persona_id, "invitacion_id": invitacion_id, "sobre": sobre}


def test_aceptacion_correcta_vincula_y_el_siguiente_pedido_entra(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    fila = _crear_invitacion(api_edificio)
    r = api_edificio.cliente.post(
        "/api/invitaciones/aceptar",
        json={"token": fila["sobre"]},
        headers=encabezados(clerk_falso, email=EMAIL, email_verified=True),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"aceptada": True}
    (estado,) = api_edificio.filas(
        "SELECT estado FROM invitacion WHERE id=%s", (fila["invitacion_id"],)
    )[0]
    assert estado == "aceptada"
    (clerk_id,) = api_edificio.filas(
        "SELECT clerk_usuario_id FROM persona WHERE id=%s", (fila["persona_id"],)
    )[0]
    assert clerk_id == sub_de(clerk_falso)
    auditorias = api_edificio.filas(
        "SELECT persona_id, entidad_id, detalle FROM auditoria WHERE accion='aceptar_invitacion'"
    )
    assert auditorias == [(fila["persona_id"], fila["persona_id"], {})]

    siguiente = api_edificio.cliente.get("/api/sesion", headers=encabezados(clerk_falso))
    assert siguiente.status_code == 200, siguiente.text
    assert any(UUID(a["id"]) == api_edificio.admin for a in siguiente.json()["administraciones"])


def test_email_en_mayusculas_coincide_tras_normalizar(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    fila = _crear_invitacion(api_edificio, email="invitada@example.invalid")
    r = api_edificio.cliente.post(
        "/api/invitaciones/aceptar",
        json={"token": fila["sobre"]},
        headers=encabezados(clerk_falso, email="INVITADA@EXAMPLE.INVALID", email_verified=True),
    )
    assert r.status_code == 200, r.text


@pytest.mark.parametrize(
    "caso",
    [
        "otro_email",
        "sin_claim_email",
        "email_no_verificado_false",
        "email_no_verificado_ausente",
        "email_no_verificado_texto",
        "token_inventado",
        "sobre_alterado",
        "invitacion_pendiente",
        "token_aceptado",
        "token_revocado",
        "token_vencido",
        "persona_ya_vinculada",
        "identidad_ya_vinculada_a_otra_persona",
    ],
)
def test_mismo_404_uniforme_sin_escribir(
    clerk_falso: rsa.RSAPrivateKey,
    api_edificio: ApiEdificio,
    monkeypatch: pytest.MonkeyPatch,
    caso: str,
) -> None:
    preparar(api_edificio, monkeypatch)
    cambios_de_claims: dict[str, Any] = {"email": EMAIL, "email_verified": True}
    estado = "enviada"
    vence_el_sobre = None
    clerk_usuario_id_previo = None

    if caso == "otro_email":
        cambios_de_claims["email"] = "otra-persona@example.invalid"
    elif caso == "sin_claim_email":
        cambios_de_claims["email"] = None
    elif caso == "email_no_verificado_false":
        cambios_de_claims["email_verified"] = False
    elif caso == "email_no_verificado_ausente":
        cambios_de_claims["email_verified"] = None
    elif caso == "email_no_verificado_texto":
        cambios_de_claims["email_verified"] = "true"
    elif caso == "invitacion_pendiente":
        estado = "pendiente"
    elif caso == "token_aceptado":
        estado = "aceptada"
    elif caso == "token_revocado":
        estado = "revocada"
    elif caso == "token_vencido":
        vence_el_sobre = datetime.now(UTC) - timedelta(days=1)
    elif caso == "persona_ya_vinculada":
        clerk_usuario_id_previo = "user_" + "0" * 32

    fila = _crear_invitacion(
        api_edificio,
        estado=estado,
        vence_el_sobre=vence_el_sobre,
        clerk_usuario_id_previo=clerk_usuario_id_previo,
    )

    if caso == "identidad_ya_vinculada_a_otra_persona":
        with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, api_edificio.admin) as s:
            s.execute(
                text(
                    "INSERT INTO persona (id, administracion_id, nombre, email, clerk_usuario_id) "
                    "VALUES (:id, :admin, 'Otra ficticia', 'otra@example.invalid', :sub)"
                ),
                {"id": uuid4(), "admin": api_edificio.admin, "sub": sub_de(clerk_falso)},
            )
            s.commit()

    cuerpo_token = fila["sobre"]
    if caso == "token_inventado":
        cuerpo_token = "token-inventado-sin-ninguna-relacion"
    elif caso == "sobre_alterado":
        cuerpo_token = (
            fila["sobre"][:-4] + ("A" if fila["sobre"][-4] != "A" else "B") + fila["sobre"][-3:]
        )

    antes = _conteos(api_edificio)
    r = api_edificio.cliente.post(
        "/api/invitaciones/aceptar",
        json={"token": cuerpo_token},
        headers=encabezados(clerk_falso, **cambios_de_claims),
    )
    assert r.status_code == 404, r.text
    assert r.json() == {"detail": "no encontrado"}
    if caso != "identidad_ya_vinculada_a_otra_persona":
        assert _conteos(api_edificio) == antes


def test_sin_sesion_valida_401_antes_del_cuerpo_y_cero_sql(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    fila = _crear_invitacion(api_edificio)
    antes = _conteos(api_edificio)

    sin_headers = api_edificio.cliente.post(
        "/api/invitaciones/aceptar", json={"token": fila["sobre"]}
    )
    assert sin_headers.status_code == 401, sin_headers.text
    assert _conteos(api_edificio) == antes

    cuerpo_roto = api_edificio.cliente.post(
        "/api/invitaciones/aceptar",
        content=b"esto no es json",
        headers={"Content-Type": "application/json"},
    )
    assert cuerpo_roto.status_code == 401, cuerpo_roto.text
    assert _conteos(api_edificio) == antes

    sin_token = api_edificio.cliente.post("/api/invitaciones/aceptar", json={})
    assert sin_token.status_code == 401, sin_token.text
    assert _conteos(api_edificio) == antes


@pytest.mark.parametrize(
    ("caso", "cuerpo", "encabezados_extra"),
    [
        ("roto", None, {}),
        ("sin_token", {}, {}),
        ("campo_extra", {"token": "x", "extra": "MARCADOR"}, {}),
        ("tipo_incorrecto", {"token": 12345}, {}),
    ],
)
def test_422_con_sesion_valida_y_cuerpo_invalido(
    clerk_falso: rsa.RSAPrivateKey,
    api_edificio: ApiEdificio,
    monkeypatch: pytest.MonkeyPatch,
    caso: str,
    cuerpo: dict[str, Any] | None,
    encabezados_extra: dict[str, str],
) -> None:
    preparar(api_edificio, monkeypatch)
    cabeceras = encabezados(clerk_falso) | encabezados_extra
    if caso == "roto":
        r = api_edificio.cliente.post(
            "/api/invitaciones/aceptar",
            content=b"{esto-no-es-json",
            headers=cabeceras | {"Content-Type": "application/json"},
        )
    else:
        r = api_edificio.cliente.post("/api/invitaciones/aceptar", json=cuerpo, headers=cabeceras)
    assert r.status_code == 422, r.text
    assert "MARCADOR" not in r.text
    assert "12345" not in r.text


def test_dos_aceptaciones_a_la_vez_dejan_un_solo_vinculo(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    fila = _crear_invitacion(api_edificio)
    from proptech_core.acceso.aplicacion.invitaciones import InvitacionNoDisponible, aceptar
    from proptech_core.acceso.dominio.token import TokenVerificado

    token_verificado = TokenVerificado(sub=sub_de(clerk_falso), email=EMAIL, email_verificado=True)

    def _intentar() -> str:
        try:
            aceptar(
                api_edificio.app.state.fabrica_de_sesiones,
                token_verificado,
                fila["sobre"],
                api_edificio.app.state.configuracion,
                uuid4(),
            )
        except InvitacionNoDisponible:
            return "rechazado"
        return "aceptado"

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(lambda _: _intentar(), range(2)))

    assert sorted(resultados) == ["aceptado", "rechazado"]
    filas = api_edificio.filas(
        "SELECT estado FROM invitacion WHERE id=%s", (fila["invitacion_id"],)
    )
    assert filas == [("aceptada",)]
    auditorias = api_edificio.filas(
        "SELECT count(*) FROM auditoria WHERE accion='aceptar_invitacion'"
    )
    assert auditorias == [(1,)]
