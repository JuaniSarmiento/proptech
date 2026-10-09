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

    return {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
    }


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
    assert "0001" in _version_actual(postgres_contenedor)

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
    postgres_contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proptech_api.salud import _verificador_real

    env = _alembic_env(postgres_contenedor)
    for clave, valor in env.items():
        if clave.startswith("POSTGRES_"):
            monkeypatch.setenv(clave, valor)

    inicio = time.monotonic()
    assert _verificador_real() is True
    assert time.monotonic() - inicio < 5

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto_libre = s.getsockname()[1]

    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", str(puerto_libre))

    inicio = time.monotonic()
    assert _verificador_real() is False
    assert time.monotonic() - inicio < 5
