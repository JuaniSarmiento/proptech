"""Permiso por acción con 403 (D7, D-096, cambio 2a, tarea 5.3), contra
PostgreSQL real, con `crear_app()` de verdad.

Contenedor propio (L-006; mismo motivo que 4.1/4.2/5.2).

Escenarios de `autorizacion-por-rol`: Colaborador asigna un edificio; Sin
permiso y fuera de alcance; Titular asigna un edificio; Asignar a una
persona de otra administración. Lecciones: L-017.
"""

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
    try:
        yield
    finally:
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
        for nombre_rol in ("titular", "colaborador", "consejo", "vecino", "destinatario"):
            pid = uuid.uuid4()
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (str(pid), str(admin_id), nombre_rol, f"{nombre_rol}@ej.com"),
            )
            personas[nombre_rol] = pid

        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
            "VALUES (%s, %s, 'titular')",
            (str(admin_id), str(personas["titular"])),
        )
        cur.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id, nivel) "
            "VALUES (%s, %s, 'colaborador', %s, 'editar')",
            (str(admin_id), str(personas["colaborador"]), str(complejo_asignado)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id) "
            "VALUES (%s, %s, 'consejo', %s)",
            (str(admin_id), str(personas["consejo"]), str(complejo_asignado)),
        )
        cur.execute(
            "INSERT INTO asignacion_rol "
            "(administracion_id, persona_id, rol, complejo_id, unidad_id) "
            "VALUES (%s, %s, 'vecino', %s, %s)",
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


def _cantidad_de_asignaciones(contenedor: PostgresContainer, administracion_id: uuid.UUID) -> int:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)", (str(administracion_id),)
            )
            cur.execute("SELECT count(*) FROM asignacion_rol")
            fila = cur.fetchone()
            assert fila is not None
            return int(fila[0])
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


# --- El titular asigna un edificio: 201, y el colaborador pasa a verlo (5.2) ---


def test_titular_asigna_un_complejo_y_el_colaborador_pasa_a_verlo(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["titular"])
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


# --- Colaborador "editar" en un complejo asignado: 403 con permiso_faltante ---


def test_colaborador_en_complejo_asignado_403_con_permiso_faltante(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["colaborador"])
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


def test_mismo_colaborador_en_complejo_no_asignado_404(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any]
) -> None:
    _como(app_real, mundo["administracion_id"], mundo["personas"]["colaborador"])
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


# --- El titular de A asignando a una persona de B: 404, nada escrito ---


def test_titular_asignando_a_persona_de_otra_administracion_404_y_nada_escrito(
    cliente: TestClient, app_real: FastAPI, contenedor: PostgresContainer, mundo: dict[str, Any]
) -> None:
    antes = _cantidad_de_asignaciones(contenedor, mundo["administracion_id"])

    _como(app_real, mundo["administracion_id"], mundo["personas"]["titular"])
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
