"""4.2: sesión por token y auditoría confirmada incluso antes de un 401."""

from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from ._api_edificios import ApiEdificio
from ._clerk import api_clerk as api_clerk
from ._clerk import clerk_falso as clerk_falso
from ._clerk import encabezados, sub_de

pytestmark = pytest.mark.integracion


def test_sesion_solo_lista_vinculos_con_asignacion(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey
) -> None:
    with api_clerk.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_clerk.admin_ajena),)
        )
        conexion.execute(
            "INSERT INTO persona (administracion_id, nombre, clerk_usuario_id) "
            "VALUES (%s, 'Sin asignación ficticia', %s)",
            (api_clerk.admin_ajena, sub_de(clerk_falso)),
        )
    respuesta = api_clerk.cliente.get("/api/sesion", headers=encabezados(clerk_falso))
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "persona": {"nombre": "Persona ficticia"},
        "administraciones": [{"id": str(api_clerk.admin), "nombre": "Inventada API"}],
    }
    with api_clerk.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_clerk.admin_ajena),)
        )
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "SELECT administracion_id, id, 'super_admin' FROM persona WHERE clerk_usuario_id = %s",
            (sub_de(clerk_falso),),
        )
    ambas = api_clerk.cliente.get("/api/sesion", headers=encabezados(clerk_falso))
    assert ambas.status_code == 200
    assert sorted(ambas.json()["administraciones"], key=lambda a: a["id"]) == sorted(
        [
            {"id": str(api_clerk.admin), "nombre": "Inventada API"},
            {"id": str(api_clerk.admin_ajena), "nombre": "Otra inventada API"},
        ],
        key=lambda a: a["id"],
    )


def test_identidad_vinculada_solo_a_b_no_muestra_nada_de_a(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio
) -> None:
    """RB2b-post-4 (revisión backend post-rompedor,
    `.git/informes-2b/revision-post-rompedor/backend.md`): `api_clerk`
    (usado arriba) ya vincula la identidad con una persona de A; acá la
    identidad está vinculada ÚNICAMENTE a B, nunca a A, y `GET
    /api/sesion` no tiene que traer nada de A."""
    sub = sub_de(clerk_falso)
    with api_edificio.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute(
            "SELECT set_config('app.administracion_id', %s, true)", (str(api_edificio.admin_ajena),)
        )
        persona = uuid4()
        conexion.execute(
            "INSERT INTO persona (id, administracion_id, nombre, clerk_usuario_id) "
            "VALUES (%s, %s, 'Sólo en B', %s)",
            (persona, api_edificio.admin_ajena, sub),
        )
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'super_admin')",
            (api_edificio.admin_ajena, persona),
        )
    respuesta = api_edificio.cliente.get("/api/sesion", headers=encabezados(clerk_falso))
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert [a["id"] for a in cuerpo["administraciones"]] == [str(api_edificio.admin_ajena)]
    assert str(api_edificio.admin) not in str(cuerpo)


def test_ingreso_deja_una_fila_con_request_id(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey
) -> None:
    seguimiento = uuid4()
    respuesta = api_clerk.cliente.post(
        "/api/sesion/ingreso",
        headers=encabezados(clerk_falso) | {"X-Request-ID": str(seguimiento)},
    )
    assert respuesta.status_code == 200
    filas = api_clerk.filas(
        "SELECT persona_id, administracion_id, request_id, detalle FROM auditoria "
        "WHERE accion = 'ingreso_exitoso'"
    )
    assert filas == [(api_clerk.personas["editar"], api_clerk.admin, seguimiento, {})]


def test_sin_asignacion_audita_y_confirma_antes_del_401(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey
) -> None:
    api_clerk.filas(
        "DELETE FROM asignacion_rol WHERE persona_id = %s RETURNING id",
        (api_clerk.personas["editar"],),
    )
    seguimiento = uuid4()
    respuesta = api_clerk.cliente.get(
        api_clerk.ruta(), headers=encabezados(clerk_falso) | {"X-Request-ID": str(seguimiento)}
    )
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Unauthorized"}
    filas = api_clerk.filas(
        "SELECT persona_id, administracion_id, request_id, detalle FROM auditoria "
        "WHERE accion = 'ingreso_fallido'"
    )
    assert filas == [
        (api_clerk.personas["editar"], api_clerk.admin, seguimiento, {"motivo": "sin_asignacion"})
    ]
    assert "user_Prueba" not in str(filas)
    assert "@" not in str(filas)
