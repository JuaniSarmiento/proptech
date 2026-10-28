"""4.2: sesión por token y auditoría confirmada incluso antes de un 401."""

from typing import Any
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from proptech_core.acceso.dominio.permisos import Accion

from ._api_edificios import ApiEdificio
from ._clerk import api_clerk as api_clerk
from ._clerk import clerk_falso as clerk_falso
from ._clerk import encabezados, sub_de

pytestmark = pytest.mark.integracion


def _sin_acciones(administraciones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """2d/7.5 (D11): estos guardas prueban qué administraciones aparecen,
    no qué puede hacer la persona ahí (eso lo prueba `test_el_super_admin`
    y `test_un_contador_por_edificio` más abajo) — se descarta `acciones`
    antes de comparar."""
    return [{k: v for k, v in a.items() if k != "acciones"} for a in administraciones]


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
    cuerpo = respuesta.json()
    assert cuerpo["persona"] == {"nombre": "Persona ficticia"}
    assert _sin_acciones(cuerpo["administraciones"]) == [
        {"id": str(api_clerk.admin), "nombre": "Inventada API"}
    ]
    assert "acciones" in cuerpo["administraciones"][0]
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
    assert sorted(_sin_acciones(ambas.json()["administraciones"]), key=lambda a: a["id"]) == sorted(
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


def test_sin_asignacion_audita_y_confirma_antes_del_403(
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
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": {"codigo": "sin_acceso"}}
    filas = api_clerk.filas(
        "SELECT persona_id, administracion_id, request_id, detalle FROM auditoria "
        "WHERE accion = 'ingreso_fallido'"
    )
    assert filas == [
        (api_clerk.personas["editar"], api_clerk.admin, seguimiento, {"motivo": "sin_asignacion"})
    ]
    assert "user_Prueba" not in str(filas)
    assert "@" not in str(filas)


@pytest.mark.parametrize("vinculada", [False, True])
def test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey, vinculada: bool
) -> None:
    ausente = api_clerk.cliente.get(
        "/api/sesion", headers=encabezados(clerk_falso, sub="user_SinPersona")
    )
    if vinculada:
        api_clerk.filas(
            "DELETE FROM asignacion_rol WHERE persona_id=%s RETURNING id",
            (api_clerk.personas["editar"],),
        )
    respuesta = api_clerk.cliente.get(
        "/api/sesion",
        headers=encabezados(clerk_falso, **({} if vinculada else {"sub": "user_Otra"})),
    )
    assert respuesta.status_code == ausente.status_code == 403
    assert respuesta.json() == {"detail": {"codigo": "sin_acceso"}}
    assert respuesta.content == ausente.content
    assert dict(respuesta.headers) | {"x-request-id": ""} == dict(ausente.headers) | {
        "x-request-id": ""
    }


@pytest.mark.parametrize("caso", ["ausente", "firma", "vencido", "aplicacion"])
def test_sesion_token_invalido_sigue_401_sin_sql(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey, caso: str
) -> None:
    from sqlalchemy import event

    h = encabezados(clerk_falso)
    if caso == "ausente":
        h = {}
    elif caso == "firma":
        h = encabezados(rsa.generate_private_key(public_exponent=65537, key_size=2048))
    elif caso == "vencido":
        h = encabezados(clerk_falso, exp=1)
    elif caso == "aplicacion":
        h = encabezados(clerk_falso, azp="https://otra.invalid")
    sql: list[str] = []

    def contar(*args: Any) -> None:
        sql.append(args[2])

    event.listen(api_clerk.app.state.engine, "before_cursor_execute", contar)
    try:
        r = api_clerk.cliente.get("/api/sesion", headers=h)
    finally:
        event.remove(api_clerk.app.state.engine, "before_cursor_execute", contar)
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}
    assert sql == []


def test_el_super_admin(clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio) -> None:
    """D11: GET /api/sesion trae, para el super admin, las tres acciones de
    administración y toda acción de edificio en `todos_los_edificios`, con
    `por_edificio` vacío."""
    api_edificio.filas(
        "UPDATE persona SET clerk_usuario_id = %s WHERE id = %s RETURNING id",
        (sub_de(clerk_falso), api_edificio.personas["super_admin"]),
    )
    respuesta = api_edificio.cliente.get("/api/sesion", headers=encabezados(clerk_falso))
    assert respuesta.status_code == 200, respuesta.text
    administraciones = {a["id"]: a for a in respuesta.json()["administraciones"]}
    acciones = administraciones[str(api_edificio.admin)]["acciones"]
    assert set(acciones["administracion"]) == {
        "crear_edificio",
        "invitar_usuarios_y_asignar_edificios",
        "ver_personal",
    }
    assert set(acciones["todos_los_edificios"]) == {a.value for a in Accion} - set(
        acciones["administracion"]
    ) - {Accion.INFORMAR_PAGO.value}
    assert acciones["por_edificio"] == {}


def test_un_contador_por_edificio(
    clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio
) -> None:
    """D11: un contador por edificio sólo trae `ver_configuracion_del_edificio`
    en `por_edificio`, con `administracion` y `todos_los_edificios` vacíos."""
    contador = uuid4()
    api_edificio.filas(
        "INSERT INTO persona (id, administracion_id, nombre, clerk_usuario_id) "
        "VALUES (%s, %s, 'Contador de edificio', %s) RETURNING id",
        (contador, api_edificio.admin, sub_de(clerk_falso)),
    )
    api_edificio.filas(
        "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
        "VALUES (%s, %s, 'contador', %s) RETURNING id",
        (api_edificio.admin, contador, api_edificio.edificio),
    )
    respuesta = api_edificio.cliente.get("/api/sesion", headers=encabezados(clerk_falso))
    assert respuesta.status_code == 200, respuesta.text
    administraciones = {a["id"]: a for a in respuesta.json()["administraciones"]}
    acciones = administraciones[str(api_edificio.admin)]["acciones"]
    assert acciones["administracion"] == []
    assert acciones["todos_los_edificios"] == []
    assert acciones["por_edificio"] == {
        str(api_edificio.edificio): [Accion.VER_CONFIGURACION_DEL_EDIFICIO.value]
    }


def test_el_403_sin_acceso_no_cambia_con_la_sesion_ampliada(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey
) -> None:
    """D11: la sesión ampliada no toca el 403 sin_acceso — comparado byte a
    byte contra el de 2.1 (`test_sesion_api.py` ya lo hace con
    `assert respuesta.json() == {"detail": {"codigo": "sin_acceso"}}` en
    los dos tests de arriba; éste lo deja escrito como escenario propio)."""
    respuesta = api_clerk.cliente.get(
        "/api/sesion", headers=encabezados(clerk_falso, sub="user_SinNingunVinculo")
    )
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": {"codigo": "sin_acceso"}}
