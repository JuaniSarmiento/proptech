"""Fixtures compartidos: PostgreSQL real por sesión de pytest (testcontainers)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from testcontainers.community.postgres import PostgresContainer

RAIZ = Path(__file__).resolve().parents[2]
_COMPOSE = RAIZ / "infra" / "compose.yaml"


def _leer_imagen_de_compose(servicio: str) -> str:
    datos = yaml.safe_load(_COMPOSE.read_text())
    imagen = datos["services"][servicio]["image"]
    assert isinstance(imagen, str)
    return imagen


IMAGEN_POSTGRES_PARA_TESTS = _leer_imagen_de_compose("db")


@pytest.fixture(scope="session")
def postgres_contenedor() -> Iterator[PostgresContainer]:
    with PostgresContainer(IMAGEN_POSTGRES_PARA_TESTS, driver="psycopg") as contenedor:
        yield contenedor
