"""Permiso por acción con 403 (D7, D-096, cambio 2a, tarea 5.3), contra
PostgreSQL real, con `crear_app()` de verdad.

Contenedor propio (L-006; mismo motivo que 4.1/4.2/5.2).

Escenarios de `autorizacion-por-rol`: Administrador asigna un edificio; Sin
permiso y fuera de alcance; Super admin asigna un edificio; Asignar a una
persona de otra administración. Lecciones: L-017.
"""

import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

from ._api_edificios import ApiEdificio
from ._edificios import devolver_tablas_protegidas

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_asignar"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


def _conectar(contenedor: PostgresContainer, usuario: str, password: str) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario,
        password=password,
        dbname=contenedor.dbname,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def contenedor() -> Iterator[PostgresContainer]:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as iniciado:
        yield iniciado


def _entorno_de_roles(contenedor: PostgresContainer) -> dict[str, str]:
    import os

    return {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD,
        "POSTGRES_APP_USER": APP_USER,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD,
        "POSTGRES_RESPALDO_USER": RESPALDO_USER,
        "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD,
    }


def _alembic_env(contenedor: PostgresContainer) -> dict[str, str]:
    entorno = dict(_entorno_de_roles(contenedor))
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _correr(args: list[str], entorno: dict[str, str]) -> None:
    subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    # D3 del 4a: la base queda como la deja el deploy real (`infra/compose.yaml`),
    # con `roles despues`; sin ese paso la API y el worker no arrancan, a propósito.
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        _entorno_de_roles(contenedor),
    )
    try:
        yield
    finally:
        devolver_tablas_protegidas(contenedor, contenedor.dbname, MIGRADOR_USER)
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


@pytest.fixture(scope="module")
def mundo(contenedor: PostgresContainer, esquema: None) -> dict[str, Any]:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    datos: dict[str, Any] = {}
    with conexion.cursor() as cur:
        admin_id = uuid.uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
        cur.execute("INSERT INTO administracion (id, nombre) VALUES (%s, %s)", (str(admin_id), "A"))

        complejo_asignado = uuid.uuid4()
        complejo_no_asignado = uuid.uuid4()
        for cid, nombre in (
            (complejo_asignado, "Asignado"),
            (complejo_no_asignado, "No asignado"),
        ):
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, %s, 'Mendoza')",
                (str(cid), str(admin_id), nombre),
            )

        unidad_del_vecino = uuid.uuid4()
        cur.execute(
            "INSERT INTO unidad (id, administracion_id, complejo_id, identificador, "
            "tipo, piso, coeficiente, superficie_m2) "
            "VALUES (%s, %s, %s, %s, 'departamento', '1', '0.1', '60.00')",
            (str(unidad_del_vecino), str(admin_id), str(complejo_asignado), "1A"),
        )

        personas: dict[str, uuid.UUID] = {}
        for nombre_rol in ("super_admin", "administrador", "consejo", "vecino", "destinatario"):
            pid = uuid.uuid4()
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (str(pid), str(admin_id), nombre_rol, f"{nombre_rol}@ej.com"),
            )
            personas[nombre_rol] = pid

        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'super_admin')",
            (str(admin_id), str(personas["super_admin"])),
        )
        cur.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id) "
            "VALUES (%s, %s, 'administrador', %s)",
            (str(admin_id), str(personas["administrador"]), str(complejo_asignado)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
            "VALUES (%s, %s, 'consejo', %s)",
            (str(admin_id), str(personas["consejo"]), str(complejo_asignado)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id, unidad_id, vinculo) "
            "VALUES (%s, %s, 'vecino', %s, %s, 'propietario')",
            (
                str(admin_id),
                str(personas["vecino"]),
                str(complejo_asignado),
                str(unidad_del_vecino),
            ),
        )
        # "destinatario" no tiene ninguna asignación: es simplemente una
        # persona existente de la misma administración, para asignarle un
        # edificio.

        # Otra administración, con una persona propia (id real, existente,
        # pero inalcanzable desde A: L-017).
        admin_b = uuid.uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_b),))
        cur.execute("INSERT INTO administracion (id, nombre) VALUES (%s, %s)", (str(admin_b), "B"))
        persona_de_b = uuid.uuid4()
        cur.execute(
            "INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
            (str(persona_de_b), str(admin_b), "de-b", "de-b@ej.com"),
        )

        datos = {
            "administracion_id": admin_id,
            "complejo_asignado": complejo_asignado,
            "complejo_no_asignado": complejo_no_asignado,
            "unidad_del_vecino": unidad_del_vecino,
            "personas": personas,
            "persona_de_b": persona_de_b,
        }
    conexion.close()
    return datos


def _cantidad_de_asignaciones(
    contenedor: PostgresContainer, administracion_id: uuid.UUID
) -> tuple[int, int]:
    conexion = _conectar(contenedor, APP_USER, APP_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)", (str(administracion_id),)
            )
            cur.execute(
                "SELECT (SELECT count(*) FROM asignacion_rol), (SELECT count(*) FROM auditoria)"
            )
            fila = cur.fetchone()
            assert fila is not None
            return int(fila[0]), int(fila[1])
    finally:
        conexion.close()


@pytest.fixture
def app_real(
    contenedor: PostgresContainer, esquema: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Iterator[FastAPI]:
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "x")
    ruta_parametros = tmp_path / "parametros.yaml"
    raiz = RAIZ_BACKEND.parent
    ruta_parametros.write_text((raiz / "config" / "parametros.yaml").read_text())
    shutil.copytree(raiz / "config" / "georef", tmp_path / "georef")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta_parametros))

    from proptech_api.app import crear_app

    app = crear_app()
    with TestClient(app):
        yield app


@pytest.fixture
def cliente(app_real: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_real) as cliente:
        yield cliente


def _como(app: FastAPI, administracion_id: uuid.UUID, persona_id: uuid.UUID) -> None:
    app.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=administracion_id, persona_id=persona_id
    )


# --- El super_admin asigna un edificio: 201, y la persona pasa a verlo (5.2) ---


def test_super_admin_asigna_un_complejo_y_la_persona_pasa_a_verlo(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["super_admin"])
    try:
        respuesta = cliente.post(
            f"/api/complejos/{mundo['complejo_no_asignado']}/asignaciones",
            json={"persona_id": str(mundo["personas"]["destinatario"]), "rol": "consejo"},
        )
        assert respuesta.status_code == 201
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)

    _como(app_real, mundo["administracion_id"], mundo["personas"]["destinatario"])
    try:
        ver = cliente.get(f"/api/complejos/{mundo['complejo_no_asignado']}")
        assert ver.status_code == 200
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- Administrador por edificio en un complejo asignado: 403 con permiso_faltante ---


def test_administrador_en_complejo_asignado_403_con_permiso_faltante(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["administrador"])
    try:
        respuesta = cliente.post(
            f"/api/complejos/{mundo['complejo_asignado']}/asignaciones",
            json={"persona_id": str(mundo["personas"]["destinatario"]), "rol": "consejo"},
        )
        assert respuesta.status_code == 403
        assert respuesta.json()["detail"] == {
            "detalle": "sin_permiso",
            "permiso_faltante": "invitar_usuarios_y_asignar_edificios",
        }
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


def test_mismo_administrador_en_complejo_no_asignado_404(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["administrador"])
    try:
        respuesta = cliente.post(
            f"/api/complejos/{mundo['complejo_no_asignado']}/asignaciones",
            json={"persona_id": str(mundo["personas"]["destinatario"]), "rol": "consejo"},
        )
        assert respuesta.status_code == 404
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- Consejo y vecino, 403 dentro de su alcance ---


@pytest.mark.parametrize("rol", ["consejo", "vecino"])
def test_consejo_y_vecino_403_dentro_de_su_alcance(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any], rol: str
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"][rol])
    try:
        respuesta = cliente.post(
            f"/api/complejos/{mundo['complejo_asignado']}/asignaciones",
            json={"persona_id": str(mundo["personas"]["destinatario"]), "rol": "consejo"},
        )
        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["permiso_faltante"] == (
            "invitar_usuarios_y_asignar_edificios"
        )
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- El super_admin de A asignando a una persona de B: 404, nada escrito ---


def test_super_admin_asignando_a_persona_de_otra_administracion_404_y_nada_escrito(
    cliente: TestClient, app_real: FastAPI, contenedor: PostgresContainer, mundo: dict[str, Any]
) -> None:
    antes = _cantidad_de_asignaciones(contenedor, mundo["administracion_id"])

    _como(app_real, mundo["administracion_id"], mundo["personas"]["super_admin"])
    try:
        respuesta = cliente.post(
            f"/api/complejos/{mundo['complejo_asignado']}/asignaciones",
            json={"persona_id": str(mundo["persona_de_b"]), "rol": "consejo"},
        )
        assert respuesta.status_code == 404
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)

    despues = _cantidad_de_asignaciones(contenedor, mundo["administracion_id"])
    assert despues == antes


@pytest.mark.parametrize("rol", ["administrador", "contador", "auxiliar", "consejo"])
def test_super_admin_asigna_perfil_alcance_y_auditoria(api_edificio: ApiEdificio, rol: str) -> None:
    api = api_edificio
    persona = api.personas["vecino"]
    api.como("vecino")
    assert api.cliente.get(f"/api/complejos/{api.otro}").status_code == 404
    api.como("super_admin")
    respuesta = api.cliente.post(
        f"/api/complejos/{api.otro}/asignaciones", json={"persona_id": str(persona), "rol": rol}
    )
    assert respuesta.status_code == 201, respuesta.text
    asignacion_id = respuesta.json()["id"]
    assert api.filas(
        "SELECT persona_id, rol, complejo_id, unidad_id, vinculo FROM asignacion_rol WHERE id = %s",
        (asignacion_id,),
    ) == [(persona, rol, api.otro, None, None)]
    assert api.filas(
        "SELECT persona_id, accion, entidad_id, detalle FROM auditoria WHERE request_id = %s",
        (respuesta.headers["X-Request-ID"],),
    ) == [
        (
            api.personas["super_admin"],
            "invitar_usuarios_y_asignar_edificios",
            api.otro,
            {
                "complejo_id": str(api.otro),
                "rol": rol,
                "alcance": "edificio",
                # RR-2: la auditoría nombra a quién recibe el perfil y la fila exacta.
                "persona_id": str(persona),
                "asignacion_id": asignacion_id,
            },
        )
    ]
    api.como("vecino")
    assert api.cliente.get(f"/api/complejos/{api.otro}").status_code == 200


def test_administrador_principal_no_asigna(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    persona = uuid.uuid4()
    with api.base.conectar_app() as conexion, conexion.transaction():
        conexion.execute("SELECT set_config('app.administracion_id', %s, true)", (str(api.admin),))
        conexion.execute(
            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Principal')",
            (persona, api.admin),
        )
        conexion.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'administrador')",
            (api.admin, persona),
        )
    api.personas["principal"] = persona
    api.como("principal")
    consulta = "SELECT (SELECT count(*) FROM asignacion_rol), (SELECT count(*) FROM auditoria)"
    antes = api.filas(consulta)
    respuesta = api.cliente.post(
        api.ruta("/asignaciones"),
        json={"persona_id": str(api.personas["vecino"]), "rol": "consejo"},
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["permiso_faltante"] == "invitar_usuarios_y_asignar_edificios"
    assert api.filas(consulta) == antes
