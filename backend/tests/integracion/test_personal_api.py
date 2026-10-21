"""5.6: listar, revocar y quitar (D5). Sólo el super admin; el `EXPLAIN`
real muestra el uso de los índices por administración y de
`ix_invitacion_persona`, sin forzar el planificador.

Escenarios de `gestion-de-usuarios`: Quitar la única asignación; Revocar
una invitación enviada; El último super admin. Lecciones: L-016.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import event, text

from proptech_core.acceso.dominio.sobres import generar
from proptech_core.compartido.base_de_datos import abrir_sesion

from ._api_edificios import ApiEdificio
from ._clerk import clerk_falso as clerk_falso
from ._clerk import encabezados, sub_de
from ._usuarios import preparar

pytestmark = pytest.mark.integracion


def test_listar_trae_personas_asignaciones_e_invitacion_vencida_calculada(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    preparar(api_edificio, monkeypatch)
    clave = api_edificio.app.state.configuracion.clave_para_invitar()
    resumen, _sobre = generar(clave, datetime.now(UTC) - timedelta(days=1))
    with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, api_edificio.admin) as sesion:
        sesion.execute(
            text(
                "INSERT INTO invitacion (id, administracion_id, persona_id, estado, "
                "token_resumen, vence, creada_por) VALUES "
                "(:id, :admin, :persona, 'enviada', :resumen, :vence, :persona)"
            ),
            {
                "id": uuid.uuid4(),
                "admin": api_edificio.admin,
                "persona": api_edificio.personas["ver"],
                "resumen": resumen,
                "vence": datetime.now(UTC) - timedelta(days=1),
            },
        )
        sesion.commit()

    api_edificio.como("super_admin")
    r = api_edificio.cliente.get("/api/personal")
    assert r.status_code == 200, r.text
    personal = {p["persona_id"]: p for p in r.json()}
    assert set(personal) == {str(p) for p in api_edificio.personas.values()}

    auxiliar = personal[str(api_edificio.personas["ver"])]
    assert auxiliar["invitacion"]["estado"] == "vencida"
    assert {a["rol"] for a in auxiliar["asignaciones"]} == {"auxiliar"}

    super_admin = personal[str(api_edificio.personas["super_admin"])]
    assert super_admin["invitacion"] is None
    assert {a["rol"] for a in super_admin["asignaciones"]} == {"super_admin"}


def test_un_no_super_admin_recibe_403_en_las_tres(api_edificio: ApiEdificio) -> None:
    api_edificio.como("ver")
    r1 = api_edificio.cliente.get("/api/personal")
    r2 = api_edificio.cliente.post(f"/api/invitaciones/{uuid.uuid4()}/revocar")
    r3 = api_edificio.cliente.delete(f"/api/asignaciones/{uuid.uuid4()}")
    for r in (r1, r2, r3):
        assert r.status_code == 403, r.text
        assert r.json()["detail"]["permiso_faltante"] == "invitar_usuarios_y_asignar_edificios"


def test_revocar_marca_revocada_encola_clerk_y_el_token_ya_no_se_acepta(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    cola = preparar(api_edificio, monkeypatch)
    email = "consejo@example.invalid"
    clave = api_edificio.app.state.configuracion.clave_para_invitar()
    resumen, sobre = generar(clave, datetime.now(UTC) + timedelta(days=7))
    invitacion_id = uuid.uuid4()
    with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, api_edificio.admin) as sesion:
        sesion.execute(
            text("UPDATE persona SET email = :email WHERE id = :persona"),
            {"email": email, "persona": api_edificio.personas["consejo"]},
        )
        sesion.execute(
            text(
                "INSERT INTO invitacion (id, administracion_id, persona_id, estado, "
                "token_resumen, vence, creada_por) VALUES "
                "(:id, :admin, :persona, 'enviada', :resumen, :vence, :persona)"
            ),
            {
                "id": invitacion_id,
                "admin": api_edificio.admin,
                "persona": api_edificio.personas["consejo"],
                "resumen": resumen,
                "vence": datetime.now(UTC) + timedelta(days=7),
            },
        )
        sesion.commit()

    api_edificio.como("super_admin")
    r = api_edificio.cliente.post(f"/api/invitaciones/{invitacion_id}/revocar")
    assert r.status_code == 200, r.text
    assert r.json() == {"revocada": True}

    assert api_edificio.filas("SELECT estado FROM invitacion WHERE id=%s", (invitacion_id,)) == [
        ("revocada",)
    ]
    assert [t["tarea"] for t in cola.trabajos] == ["revocar_invitacion_en_clerk"]
    assert cola.trabajos[0]["invitacion_id"] == str(invitacion_id)
    assert api_edificio.filas(
        "SELECT count(*) FROM auditoria WHERE accion='revocar_invitacion'"
    ) == [(1,)]

    # El token ya no se acepta: mismo 404 uniforme de 5.5 (llamada directa a
    # la aplicación, sin pasar por HTTP: el sobre sigue siendo válido, lo
    # que cambió es el estado de la fila).
    from proptech_core.acceso.aplicacion.invitaciones import InvitacionNoDisponible, aceptar
    from proptech_core.acceso.dominio.token import TokenVerificado

    with pytest.raises(InvitacionNoDisponible):
        aceptar(
            api_edificio.app.state.fabrica_de_sesiones,
            TokenVerificado(sub="user_" + "0" * 32, email=email, email_verificado=True),
            sobre,
            api_edificio.app.state.configuracion,
            uuid.uuid4(),
        )


def test_quitar_la_unica_asignacion_de_un_auxiliar_da_401_en_su_proximo_pedido(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio
) -> None:
    sub = sub_de(clerk_falso)
    api_edificio.filas(
        "UPDATE persona SET clerk_usuario_id=%s WHERE id=%s RETURNING id",
        (sub, api_edificio.personas["ver"]),
    )
    (asignacion_id,) = api_edificio.filas(
        "SELECT id FROM asignacion_rol WHERE persona_id=%s", (api_edificio.personas["ver"],)
    )[0]

    api_edificio.como("super_admin")
    r = api_edificio.cliente.delete(f"/api/asignaciones/{asignacion_id}")
    assert r.status_code == 200, r.text
    assert r.json() == {"quitada": True}
    assert api_edificio.filas(
        "SELECT count(*) FROM auditoria WHERE accion='quitar_asignacion'"
    ) == [(1,)]

    from proptech_api.acceso import identidad_actual

    api_edificio.app.dependency_overrides.pop(identidad_actual, None)
    siguiente = api_edificio.cliente.post(
        "/api/sesion/ingreso", headers=encabezados(clerk_falso, sub=sub)
    )
    assert siguiente.status_code == 401, siguiente.text


def test_el_unico_super_admin_no_puede_quitarse_su_asignacion(api_edificio: ApiEdificio) -> None:
    (asignacion_id,) = api_edificio.filas(
        "SELECT id FROM asignacion_rol WHERE persona_id=%s",
        (api_edificio.personas["super_admin"],),
    )[0]
    api_edificio.como("super_admin")
    r = api_edificio.cliente.delete(f"/api/asignaciones/{asignacion_id}")
    assert r.status_code == 409, r.text
    assert r.json() == {"detail": "conflicto", "campo": "super_admin"}
    assert api_edificio.filas(
        "SELECT count(*) FROM asignacion_rol WHERE id=%s", (asignacion_id,)
    ) == [(1,)]


def test_explain_el_listado_usa_los_indices_por_administracion_y_de_invitacion(
    api_edificio: ApiEdificio,
) -> None:
    from proptech_core.acceso.aplicacion.usuarios import listar_personal

    # Volumen real (sin forzar el planificador, mismo criterio que
    # `test_alcance_api`): con sólo las 5 personas de la fixture, Postgres
    # prefiere `Seq Scan` en una tabla de ese tamaño sin importar el índice.
    with abrir_sesion(api_edificio.app.state.fabrica_de_sesiones, api_edificio.admin) as sesion:
        for _ in range(400):
            persona_id = uuid.uuid4()
            sesion.execute(
                text(
                    "INSERT INTO persona (id, administracion_id, nombre, email) "
                    "VALUES (:id, :admin, 'Relleno', :email)"
                ),
                {
                    "id": persona_id,
                    "admin": api_edificio.admin,
                    "email": f"relleno-{persona_id}@example.invalid",
                },
            )
            sesion.execute(
                text(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
                    "VALUES (:admin, :persona, 'auxiliar', :edificio)"
                ),
                {
                    "admin": api_edificio.admin,
                    "persona": persona_id,
                    "edificio": api_edificio.edificio,
                },
            )
            resumen = uuid.uuid4().bytes + uuid.uuid4().bytes
            sesion.execute(
                text(
                    "INSERT INTO invitacion (administracion_id, persona_id, estado, "
                    "token_resumen, vence, creada_por) VALUES "
                    "(:admin, :persona, 'enviada', :resumen, now() + interval '7 days', :persona)"
                ),
                {"admin": api_edificio.admin, "persona": persona_id, "resumen": resumen},
            )
        sesion.commit()
        sesion.execute(text("ANALYZE persona, asignacion_rol, invitacion"))
        sesion.commit()

        consultas: list[tuple[str, Any]] = []

        def capturar(_c: Any, _cur: Any, sentencia: str, parametros: Any, *_a: Any) -> None:
            consultas.append((sentencia, parametros))

        conexion = sesion.connection()
        event.listen(conexion, "before_cursor_execute", capturar)
        try:
            listar_personal(sesion)
        finally:
            event.remove(conexion, "before_cursor_execute", capturar)

        assert len(consultas) == 3
        planes = []
        for sentencia, parametros in consultas:
            plan = "\n".join(conexion.exec_driver_sql("EXPLAIN " + sentencia, parametros).scalars())
            planes.append(plan)
            print(f"proptech_app; SET LOCAL app.administracion_id = '{api_edificio.admin}';")
            print(sentencia)
            print(plan)

    # Los tres por administración (RLS, nunca un `WHERE` propio) y el de
    # invitaciones específicamente por `ix_invitacion_persona` (D5).
    assert "administracion_id" in planes[0] and (
        "uq_persona_administracion_email" in planes[0]
        or "uq_persona_clerk_administracion" in planes[0]
    )
    assert "ix_asignacion_rol_persona" in planes[1]
    assert "ix_invitacion_persona" in planes[2]
