"""Tests de integración: PostgreSQL real (testcontainers), Alembic y el verificador real."""

import socket
import subprocess
import time
from pathlib import Path

import pytest
from testcontainers.community.postgres import PostgresContainer

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integracion


def _alembic_env(contenedor: PostgresContainer) -> dict[str, str]:
    import os

    from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION

    entorno = {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        # El rol real del migrador (D1, D2, tarea 2.2), que `roles_reales` ya creó.
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD_DE_SESION,
        "POSTGRES_DB": contenedor.dbname,
    }
    # 6.1/D11: Alembic no depende de Redis ni de los parámetros del sistema.
    # Se borran explícitamente (no basta con no setearlas: el fixture de
    # integración las deja puestas en el entorno del proceso de pytest, y
    # `**os.environ` las heredaría en silencio) para probar que el trabajo
    # de migraciones corre sin ellas.
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _version_actual(contenedor: PostgresContainer) -> str:
    resultado = subprocess.run(
        ["uv", "run", "alembic", "current"],
        cwd=RAIZ_BACKEND,
        env=_alembic_env(contenedor),
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout.strip()


def test_upgrade_head_registra_0001_y_downgrade_la_deja_sin_revision(
    postgres_contenedor: PostgresContainer,
    roles_reales: None,
) -> None:
    env = _alembic_env(postgres_contenedor)

    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    # No se fija a "0001": la migración 0002 (cambio 1c, tarea 5.1) agregó una
    # revisión después, y "head" avanza con cada migración nueva. Lo que este
    # test afirma es que "upgrade head" deja la base en la punta de la cadena.
    assert "(head)" in _version_actual(postgres_contenedor)

    subprocess.run(
        ["uv", "run", "alembic", "downgrade", "base"],
        cwd=RAIZ_BACKEND,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert _version_actual(postgres_contenedor) == ""


def test_verificador_real_contra_el_contenedor_y_contra_puerto_sin_servidor(
    postgres_contenedor: PostgresContainer,
    monkeypatch: pytest.MonkeyPatch,
    roles_reales: None,
) -> None:
    from proptech_api.salud import _verificador_con_engine
    from proptech_core.compartido.base_de_datos import crear_engine
    from proptech_core.compartido.configuracion import Configuracion

    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    env = _alembic_env(postgres_contenedor)
    for clave, valor in env.items():
        if clave.startswith("POSTGRES_"):
            monkeypatch.setenv(clave, valor)
    # `Configuracion` (D3) lee el par real de la app (tarea 2.2), que
    # `roles_reales` ya creó.
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)

    engine_contenedor = crear_engine(Configuracion())
    try:
        inicio = time.monotonic()
        assert _verificador_con_engine(engine_contenedor)() is True
        assert time.monotonic() - inicio < 5
    finally:
        engine_contenedor.dispose()

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto_libre = s.getsockname()[1]

    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", str(puerto_libre))

    engine_sin_servidor = crear_engine(Configuracion())
    try:
        inicio = time.monotonic()
        assert _verificador_con_engine(engine_sin_servidor)() is False
        assert time.monotonic() - inicio < 5
    finally:
        engine_sin_servidor.dispose()
