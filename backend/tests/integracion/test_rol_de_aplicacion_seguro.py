"""`verificar_rol_de_aplicacion_seguro` contra PostgreSQL real (D1, D2, cambio
2a, vuelta 2, R8): la API y el worker no arrancan si la conexión con la que
quedaron, en los hechos, no es segura para un servicio permanente.

Contenedor propio (L-006). Escenario de `entorno-de-ejecucion`, "Ningún
servicio permanente MUST recibir la contraseña del rol de arranque".
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    RolDeAplicacionInseguro,
    verificar_rol_de_aplicacion_seguro,
)

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_rol_seguro"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


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


def _engine_como(contenedor: PostgresContainer, usuario: str, password: str) -> Engine:
    return create_engine(
        f"postgresql+psycopg://{usuario}:{password}@"
        f"{contenedor.get_container_host_ip()}:{contenedor.get_exposed_port(5432)}/"
        f"{contenedor.dbname}"
    )


def test_la_app_es_un_rol_seguro(contenedor: PostgresContainer, esquema: None) -> None:
    engine = _engine_como(contenedor, APP_USER, APP_PASSWORD)
    try:
        verificar_rol_de_aplicacion_seguro(engine)  # no levanta
    finally:
        engine.dispose()


def test_el_respaldo_no_es_seguro_por_bypassrls(
    contenedor: PostgresContainer, esquema: None
) -> None:
    engine = _engine_como(contenedor, RESPALDO_USER, RESPALDO_PASSWORD)
    try:
        with pytest.raises(RolDeAplicacionInseguro, match="BYPASSRLS"):
            verificar_rol_de_aplicacion_seguro(engine)
    finally:
        engine.dispose()


def test_el_migrador_no_es_seguro_por_ser_dueno_de_tablas(
    contenedor: PostgresContainer, esquema: None
) -> None:
    engine = _engine_como(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    try:
        with pytest.raises(RolDeAplicacionInseguro, match="dueño de"):
            verificar_rol_de_aplicacion_seguro(engine)
    finally:
        engine.dispose()


def test_el_rol_de_arranque_no_es_seguro_por_ser_superusuario(
    contenedor: PostgresContainer, esquema: None
) -> None:
    engine = _engine_como(contenedor, contenedor.username, contenedor.password)
    try:
        with pytest.raises(RolDeAplicacionInseguro, match="superusuario"):
            verificar_rol_de_aplicacion_seguro(engine)
    finally:
        engine.dispose()
