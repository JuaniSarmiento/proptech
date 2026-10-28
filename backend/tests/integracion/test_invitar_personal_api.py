"""5.2: permiso E6, perfiles, reuso y rotación de la invitación."""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ._api_edificios import ApiEdificio
from ._usuarios import preparar

pytestmark = pytest.mark.integracion
RUTA = "/api/personal/invitaciones"


def cuerpo(api: ApiEdificio, rol: str = "contador", alcance: str = "principal") -> dict[str, Any]:
    return {
        "nombre": "Personal ficticio",
        "email": "PERSONAL@example.invalid",
        "rol": rol,
        "alcance": alcance,
        "complejo_id": str(api.edificio) if alcance == "edificio" else None,
    }


def cantidades(api: ApiEdificio) -> tuple[int, ...]:
    return tuple(
        api.filas(
            "SELECT (SELECT count(*) FROM persona), "
            "(SELECT count(*) FROM asignacion_rol), "
            "(SELECT count(*) FROM invitacion), "
            "(SELECT count(*) FROM auditoria)"
        )[0]
    )


@pytest.mark.parametrize(
    ("rol", "alcance"),
    [
        ("administrador", "principal"),
        ("administrador", "edificio"),
        ("contador", "principal"),
        ("contador", "edificio"),
        ("auxiliar", "edificio"),
        ("consejo", "edificio"),
    ],
)
def test_super_admin_invita(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch, rol: str, alcance: str
) -> None:
    from proptech_core.acceso.dominio.sobres import abrir

    cola = preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    if rol == "contador" and alcance == "principal":
        from proptech_core.compartido.parametros import Invitaciones

        api_edificio.app.state.parametros = api_edificio.app.state.parametros.model_copy(
            update={"invitaciones": Invitaciones(vencimiento_dias=3)}
        )
    antes = datetime.now(UTC)
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio, rol, alcance))
    assert r.status_code == 201, r.text
    persona, asignacion, invitacion = (
        r.json()[campo] for campo in ("persona_id", "asignacion_id", "invitacion_id")
    )
    assert api_edificio.filas("SELECT email FROM persona WHERE id=%s", (persona,)) == [
        ("personal@example.invalid",)
    ]
    fila = api_edificio.filas(
        "SELECT rol,complejo_id FROM asignacion_rol WHERE id=%s", (asignacion,)
    )[0]
    assert fila == (rol, api_edificio.edificio if alcance == "edificio" else None)
    estado, resumen, vence = api_edificio.filas(
        "SELECT estado,token_resumen,vence FROM invitacion WHERE id=%s", (invitacion,)
    )[0]
    assert estado == "pendiente" and len(resumen) == 32
    dias = api_edificio.app.state.parametros.invitaciones.vencimiento_dias
    assert antes + timedelta(days=dias) <= vence <= datetime.now(UTC) + timedelta(days=dias)
    trabajo = cola.trabajos[0]
    assert set(trabajo) == {
        "tarea",
        "clave",
        "request_id",
        "expira_en_s",
        "administracion_id",
        "invitacion_id",
        "sobre",
    }
    crudo = abrir(
        api_edificio.app.state.configuracion.clave_para_invitar(),
        trabajo["sobre"],
        datetime.now(UTC),
    )
    assert hashlib.sha256(crudo.encode()).digest() == resumen
    assert crudo not in str(trabajo) and "@" not in str(trabajo)
    assert trabajo["sobre"] not in r.text and resumen.hex() not in r.text and "email" not in r.text
    detalle = api_edificio.filas("SELECT detalle FROM auditoria WHERE accion='invitar_personal'")[
        0
    ][0]
    assert detalle == {
        "persona_id": persona,
        "asignacion_id": asignacion,
        "rol": rol,
        "alcance": alcance,
    }


@pytest.mark.parametrize("actor", ["editar", "ver", "vecino"])
def test_solo_super_admin_sin_escribir(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch, actor: str
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    if actor != "vecino":
        api_edificio.filas(
            "UPDATE asignacion_rol SET complejo_id=NULL, rol=%s WHERE persona_id=%s RETURNING id",
            ("contador" if actor == "ver" else "administrador", api_edificio.personas[actor]),
        )
    api_edificio.como(actor)
    antes = cantidades(api_edificio)
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio))
    assert r.status_code == 403
    assert r.json()["detail"]["permiso_faltante"] == "invitar_usuarios_y_asignar_edificios"
    assert cantidades(api_edificio) == antes and cola.trabajos == []


@pytest.mark.parametrize(
    ("cambios", "estado", "campo"),
    [
        ({"rol": "auxiliar"}, 422, "alcance"),
        ({"rol": "consejo"}, 422, "alcance"),
        ({"rol": "super_admin"}, 422, "rol"),
        ({"rol": "vecino"}, 422, "rol"),
        ({"extra": "MARCADOR"}, 422, "extra"),
        ({"email": "MARCADOR"}, 422, "email"),
    ],
)
def test_cuerpos_invalidos(
    api_edificio: ApiEdificio,
    monkeypatch: pytest.MonkeyPatch,
    cambios: dict[str, Any],
    estado: int,
    campo: str,
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    antes = cantidades(api_edificio)
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio) | cambios)
    assert r.status_code == estado, r.text
    assert campo in str(r.json()["detail"]) and "MARCADOR" not in r.text
    assert cantidades(api_edificio) == antes and cola.trabajos == []


def test_ajeno_y_duplicado(api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch) -> None:
    preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    antes = cantidades(api_edificio)
    r = api_edificio.cliente.post(
        RUTA,
        json=cuerpo(api_edificio, "auxiliar", "edificio")
        | {"complejo_id": str(api_edificio.ajeno)},
    )
    assert r.status_code == 404 and cantidades(api_edificio) == antes
    assert api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio)).status_code == 201
    antes = cantidades(api_edificio)
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio))
    assert r.status_code == 409 and r.json() == {"detail": "conflicto", "campo": "rol"}
    assert cantidades(api_edificio) == antes


@pytest.mark.parametrize("estado", ["pendiente", "enviada", "fallida", "vencida"])
def test_reinvitar_revoca_la_anterior(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch, estado: str
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    primera = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio)).json()
    api_edificio.filas(
        "UPDATE invitacion SET estado=%s, vence=%s WHERE id=%s RETURNING id",
        (
            "enviada" if estado == "vencida" else estado,
            datetime.now(UTC) + timedelta(days=-1 if estado == "vencida" else 7),
            primera["invitacion_id"],
        ),
    )
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio, "contador", "edificio"))
    assert r.status_code == 201, r.text
    assert r.json()["persona_id"] == primera["persona_id"]
    assert api_edificio.filas(
        "SELECT estado FROM invitacion WHERE id=%s", (primera["invitacion_id"],)
    ) == [("revocada",)]
    assert api_edificio.filas(
        "SELECT count(*) FROM invitacion WHERE estado IN ('pendiente','enviada','fallida')"
    ) == [(1,)]
    assert [t["tarea"] for t in cola.trabajos] == [
        "enviar_invitacion",
        "revocar_invitacion_en_clerk",
        "enviar_invitacion",
    ]


def test_persona_vinculada_solo_suma_asignacion(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    api_edificio.filas(
        "INSERT INTO persona(administracion_id,nombre,email,clerk_usuario_id) "
        "VALUES (%s,'Ya vinculada','personal@example.invalid','user_Vinculada') RETURNING id",
        (api_edificio.admin,),
    )
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio))
    assert r.status_code == 201 and r.json()["invitacion_id"] is None
    assert cola.trabajos == [] and api_edificio.filas("SELECT count(*) FROM invitacion") == [(0,)]


# --- D12 (2d, 7.7): reinvitar el mismo email deja el nombre nuevo ---


def test_reinvitar_el_mismo_email_con_otro_nombre(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    primera = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio) | {"nombre": "Ana"}).json()
    api_edificio.filas(
        "UPDATE invitacion SET estado='revocada' WHERE id=%s RETURNING id",
        (primera["invitacion_id"],),
    )
    r = api_edificio.cliente.post(
        RUTA, json=cuerpo(api_edificio, "administrador", "edificio") | {"nombre": "Ana María"}
    )
    assert r.status_code == 201, r.text
    assert r.json()["persona_id"] == primera["persona_id"]
    personal = api_edificio.cliente.get("/api/personal").json()
    persona = next(p for p in personal if p["persona_id"] == primera["persona_id"])
    assert persona["nombre"] == "Ana María"
    assert {a["rol"] for a in persona["asignaciones"]} == {"contador", "administrador"}


def test_reinvitar_el_email_del_super_admin_no_lo_renombra(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    email_sa = api_edificio.filas(
        "UPDATE persona SET email='super@example.invalid' WHERE id=%s RETURNING email",
        (api_edificio.personas["super_admin"],),
    )[0][0]
    api_edificio.como("super_admin")
    r = api_edificio.cliente.post(
        RUTA,
        json=cuerpo(api_edificio, "administrador", "edificio")
        | {"nombre": "Otro", "email": email_sa},
    )
    assert r.status_code == 201, r.text
    assert api_edificio.filas(
        "SELECT nombre FROM persona WHERE id=%s", (api_edificio.personas["super_admin"],)
    ) == [("Persona ficticia",)]


def test_reinvitar_en_una_administracion_no_renombra_en_otra(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    email = "compartido@example.invalid"
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin_ajena),)
        )
        conexion.execute(
            "INSERT INTO persona(administracion_id,nombre,email) VALUES (%s,'Persona de B',%s)",
            (api_edificio.admin_ajena, email),
        )
    api_edificio.como("super_admin")
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio) | {"email": email})
    assert r.status_code == 201, r.text
    assert api_edificio.filas(
        "SELECT estado FROM invitacion WHERE id=%s", (r.json()["invitacion_id"],)
    ) == [("pendiente",)]
    api_edificio.filas(
        "UPDATE invitacion SET estado='revocada' WHERE id=%s RETURNING id",
        (r.json()["invitacion_id"],),
    )
    r2 = api_edificio.cliente.post(
        RUTA, json=cuerpo(api_edificio, "administrador", "edificio") | {"email": email}
    )
    assert r2.status_code == 201, r2.text
    assert api_edificio.filas(
        "SELECT nombre FROM persona WHERE id=%s", (r2.json()["persona_id"],)
    ) == [("Personal ficticio",)]
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin_ajena),)
        )
        fila_b = conexion.execute("SELECT nombre FROM persona WHERE email=%s", (email,)).fetchone()
    assert fila_b == ("Persona de B",)


def test_reinvitar_una_persona_ya_vinculada_tambien_renombra(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D12: "lo mismo con la persona ya vinculada" — `_alta` es la misma
    función para la persona vinculada y la no vinculada."""
    preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    api_edificio.filas(
        "INSERT INTO persona(administracion_id,nombre,email,clerk_usuario_id) "
        "VALUES (%s,'Nombre viejo','personal@example.invalid','user_Vinculada') RETURNING id",
        (api_edificio.admin,),
    )
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio) | {"nombre": "Nombre nuevo"})
    assert r.status_code == 201, r.text
    assert api_edificio.filas(
        "SELECT nombre FROM persona WHERE id=%s", (r.json()["persona_id"],)
    ) == [("Nombre nuevo",)]


def test_dar_de_alta_vecino_tambien_renombra(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D12: "lo mismo ... por el alta de vecinos" — el spec ya dice que las
    reglas de reuso de la persona son las del personal."""
    preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    email = "vecino-reinvitado@example.invalid"
    primera = api_edificio.cliente.post(
        f"/api/unidades/{api_edificio.otra_unidad}/vecinos",
        json={"nombre": "Vecino viejo", "email": email, "vinculo": "propietario"},
    ).json()
    api_edificio.filas(
        "UPDATE invitacion SET estado='revocada' WHERE id=%s RETURNING id",
        (primera["invitacion_id"],),
    )
    r = api_edificio.cliente.post(
        f"/api/unidades/{api_edificio.unidad}/vecinos",
        json={"nombre": "Vecino nuevo", "email": email, "vinculo": "inquilino"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["persona_id"] == primera["persona_id"]
    assert api_edificio.filas(
        "SELECT nombre FROM persona WHERE id=%s", (primera["persona_id"],)
    ) == [("Vecino nuevo",)]


def test_el_nombre_no_cambia_si_la_invitacion_se_rechaza(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    api_edificio.como("super_admin")
    primera = api_edificio.cliente.post(
        RUTA, json=cuerpo(api_edificio) | {"nombre": "Nombre original"}
    ).json()
    r = api_edificio.cliente.post(RUTA, json=cuerpo(api_edificio) | {"nombre": "Otra"})
    assert r.status_code == 409
    assert r.json() == {"detail": "conflicto", "campo": "rol"}
    assert api_edificio.filas(
        "SELECT nombre FROM persona WHERE id=%s", (primera["persona_id"],)
    ) == [("Nombre original",)]
