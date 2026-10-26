"""Identidad inyectable y orden de dependencias (D7, cambio 2a, tarea 4.2),
contra PostgreSQL real, con `crear_app()` de verdad.

Contenedor propio (L-006), nunca el de sesión: ver el comentario largo en
`test_tenant_por_transaccion.py` (mismo problema de orden entre archivos,
encontrado corriendo la suite completa, L-013/L-016).

La identidad se inyecta con `app.dependency_overrides[identidad_actual]`
(D7: hasta el 2b no hay otra forma); sin eso, los tres endpoints tienen que
responder 401 sin tocar la base.

Escenarios de `autorizacion-por-rol`: Pedido sin identidad. Escenarios de
`aislamiento-por-administracion`: Encabezado o parámetro con otra
administración. Lecciones: L-017 (los ids de otra administración son UUID
válidos y existentes, nunca un texto que FastAPI ya rechaza con 422).
"""

import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from testcontainers.community.postgres import PostgresContainer

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

from ._edificios import devolver_tablas_protegidas

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_identidad"
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
def dos_administraciones_con_complejo_y_unidad(
    contenedor: PostgresContainer, esquema: None
) -> dict[str, Any]:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    datos: dict[str, Any] = {}
    with conexion.cursor() as cur:
        for clave in ("a", "b"):
            admin_id = uuid.uuid4()
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                (str(admin_id), f"Tenant {clave.upper()}"),
            )
            complejo_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, %s, 'Mendoza')",
                (str(complejo_id), str(admin_id), f"Complejo {clave.upper()}"),
            )
            unidad_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO unidad (id, administracion_id, complejo_id, identificador, "
                "tipo, piso, coeficiente, superficie_m2) "
                "VALUES (%s, %s, %s, %s, 'departamento', '1', '0.1', '60.00')",
                (str(unidad_id), str(admin_id), str(complejo_id), f"1A-{clave}"),
            )
            persona_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (str(persona_id), str(admin_id), f"Persona {clave}", f"persona-{clave}@ej.com"),
            )
            # Super admin (alcanza todo, D-096): esta tarea prueba el cableado de
            # identidad, no el alcance por rol (eso es la tarea 5.2).
            cur.execute(
                "INSERT INTO asignacion_rol (administracion_id, persona_id, rol) "
                "VALUES (%s, %s, 'super_admin')",
                (str(admin_id), str(persona_id)),
            )
            datos[clave] = {
                "administracion_id": admin_id,
                "complejo_id": complejo_id,
                "unidad_id": unidad_id,
                "persona_id": persona_id,
            }
    conexion.close()
    return datos


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
    with TestClient(app):  # dispara el lifespan (crea el engine real)
        yield app


@pytest.fixture
def cliente(app_real: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_real) as cliente:
        yield cliente


def _contar_sentencias(app: FastAPI) -> list[int]:
    contador = [0]

    @event.listens_for(app.state.engine, "before_cursor_execute")
    def _contar(*_args: object, **_kwargs: object) -> None:
        contador[0] += 1

    return contador


# --- Sin dependency_overrides: 401 en los tres, sin tocar la base ---


@pytest.mark.parametrize("metodo_y_ruta", ["GET /api/complejos/{id}", "GET /api/unidades/{id}"])
def test_sin_identidad_401_sin_ejecutar_sql(
    cliente: TestClient,
    app_real: FastAPI,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
    metodo_y_ruta: str,
) -> None:
    contador = _contar_sentencias(app_real)
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    if "complejos" in metodo_y_ruta:
        respuesta = cliente.get(f"/api/complejos/{admin_a['complejo_id']}")
    else:
        respuesta = cliente.get(f"/api/unidades/{admin_a['unidad_id']}")
    assert respuesta.status_code == 401
    assert contador[0] == 0, "se ejecutó SQL antes de resolver la identidad"


def test_post_sin_identidad_401_sin_ejecutar_sql(
    cliente: TestClient,
    app_real: FastAPI,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
) -> None:
    contador = _contar_sentencias(app_real)
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    respuesta = cliente.post(
        f"/api/complejos/{admin_a['complejo_id']}/asignaciones",
        json={"persona_id": str(admin_a["persona_id"]), "rol": "consejo"},
    )
    assert respuesta.status_code == 401
    assert contador[0] == 0, "se ejecutó SQL antes de resolver la identidad"


# --- Encabezado, parámetro o cuerpo con otra administración: no cambian el tenant ---


def test_encabezado_x_administracion_id_no_cambia_el_tenant(
    cliente: TestClient,
    app_real: FastAPI,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
) -> None:
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    admin_b = dos_administraciones_con_complejo_y_unidad["b"]
    app_real.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=admin_a["administracion_id"], persona_id=admin_a["persona_id"]
    )
    try:
        respuesta = cliente.get(
            f"/api/complejos/{admin_a['complejo_id']}",
            headers={"X-Administracion-Id": str(admin_b["administracion_id"])},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["administracion_id"] == str(admin_a["administracion_id"])

        # El complejo de B no aparece aunque el id exista de verdad (L-017).
        respuesta_b = cliente.get(
            f"/api/complejos/{admin_b['complejo_id']}",
            headers={"X-Administracion-Id": str(admin_b["administracion_id"])},
        )
        assert respuesta_b.status_code == 404
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


def test_parametro_administracion_id_no_cambia_el_tenant(
    cliente: TestClient,
    app_real: FastAPI,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
) -> None:
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    admin_b = dos_administraciones_con_complejo_y_unidad["b"]
    app_real.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=admin_a["administracion_id"], persona_id=admin_a["persona_id"]
    )
    try:
        respuesta = cliente.get(
            f"/api/unidades/{admin_a['unidad_id']}",
            params={"administracion_id": str(admin_b["administracion_id"])},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["administracion_id"] == str(admin_a["administracion_id"])
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


def test_campo_administracion_id_en_el_cuerpo_no_cambia_el_tenant(
    cliente: TestClient,
    app_real: FastAPI,
    contenedor: PostgresContainer,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
) -> None:
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    admin_b = dos_administraciones_con_complejo_y_unidad["b"]
    app_real.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=admin_a["administracion_id"], persona_id=admin_a["persona_id"]
    )
    try:
        respuesta = cliente.post(
            f"/api/complejos/{admin_a['complejo_id']}/asignaciones",
            json={
                "persona_id": str(admin_a["persona_id"]),
                "rol": "consejo",
                # Intenta mandar el tenant de B en el cuerpo: se ignora (D7).
                "administracion_id": str(admin_b["administracion_id"]),
            },
        )
        assert respuesta.status_code == 201
        fila_id = respuesta.json()["id"]
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)

    # Verificado desde afuera, como el migrador con el tenant de A: la fila
    # quedó de A, nunca de B, aunque el cuerpo lo haya pedido.
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)",
                (str(admin_a["administracion_id"]),),
            )
            cur.execute("SELECT administracion_id FROM asignacion_rol WHERE id = %s", (fila_id,))
            fila = cur.fetchone()
            assert fila is not None
            assert fila[0] == admin_a["administracion_id"]
    finally:
        conexion.close()


# --- Dos pedidos seguidos con identidades distintas no se contagian ---


def test_dos_pedidos_seguidos_con_identidades_distintas_no_se_contagian(
    cliente: TestClient,
    app_real: FastAPI,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
) -> None:
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    admin_b = dos_administraciones_con_complejo_y_unidad["b"]

    app_real.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=admin_a["administracion_id"], persona_id=admin_a["persona_id"]
    )
    respuesta_a = cliente.get(f"/api/complejos/{admin_a['complejo_id']}")
    assert respuesta_a.status_code == 200
    assert respuesta_a.json()["administracion_id"] == str(admin_a["administracion_id"])

    app_real.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=admin_b["administracion_id"], persona_id=admin_b["persona_id"]
    )
    try:
        # El mismo complejo de A, pedido ahora con la identidad de B: no se
        # contagia nada del pedido anterior (404, no 200 con datos de A).
        respuesta_b = cliente.get(f"/api/complejos/{admin_a['complejo_id']}")
        assert respuesta_b.status_code == 404

        respuesta_b_propio = cliente.get(f"/api/complejos/{admin_b['complejo_id']}")
        assert respuesta_b_propio.status_code == 200
        assert respuesta_b_propio.json()["administracion_id"] == str(admin_b["administracion_id"])
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- La misma batería con una dependencia de sesión `async def` (D4) ---


async def _identidad_actual_async() -> Identidad:
    raise HTTPException(status_code=401)


def test_con_dependencia_async_la_identidad_sigue_filtrando_por_tenant(
    cliente: TestClient,
    app_real: FastAPI,
    dos_administraciones_con_complejo_y_unidad: dict[str, Any],
) -> None:
    """D4, punto 5 del arquitecto: el tenant vive en `session.info`, no en
    una `ContextVar`, así que da igual si la dependencia que resuelve la
    identidad es sincrónica o `async def`."""
    admin_a = dos_administraciones_con_complejo_y_unidad["a"]
    admin_b = dos_administraciones_con_complejo_y_unidad["b"]

    async def _identidad_de_a() -> Identidad:
        return Identidad(
            administracion_id=admin_a["administracion_id"], persona_id=admin_a["persona_id"]
        )

    app_real.dependency_overrides[identidad_actual] = _identidad_de_a
    try:
        respuesta = cliente.get(
            f"/api/complejos/{admin_a['complejo_id']}",
            headers={"X-Administracion-Id": str(admin_b["administracion_id"])},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["administracion_id"] == str(admin_a["administracion_id"])
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)

    # Sin override: la versión async de identidad_actual también da 401.
    app_real.dependency_overrides[identidad_actual] = _identidad_actual_async
    try:
        respuesta_401 = cliente.get(f"/api/complejos/{admin_a['complejo_id']}")
        assert respuesta_401.status_code == 401
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)
