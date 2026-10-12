"""D12: la imagen que de verdad corrió se compara contra compose.yaml, no el
fixture contra sí mismo (reemplaza el test tautológico de D-051)."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from testcontainers.community.postgres import PostgresContainer

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RAIZ = RAIZ_BACKEND.parent
COMPOSE = RAIZ / "infra" / "compose.yaml"

pytestmark = pytest.mark.integracion


def _imagen_compose_db() -> str:
    datos: dict[str, Any] = yaml.safe_load(COMPOSE.read_text())
    imagen = datos["services"]["db"]["image"]
    assert isinstance(imagen, str)
    return imagen


def _tags_reales(contenedor: PostgresContainer) -> list[str]:
    crudo = contenedor.get_wrapped_container()
    tags = crudo.image.tags
    assert isinstance(tags, list)
    return tags


def test_imagen_real_de_postgres_coincide_con_compose_db(
    postgres_contenedor: PostgresContainer,
) -> None:
    imagen_compose = _imagen_compose_db()
    tags_reales = _tags_reales(postgres_contenedor)
    assert imagen_compose in tags_reales, (
        f"compose.yaml pide '{imagen_compose}' pero el contenedor que corrió "
        f"tiene las etiquetas {tags_reales}"
    )


def test_imagen_real_de_postgres_no_coincide_si_se_fuerza_otra(
    postgres_contenedor: PostgresContainer,
) -> None:
    """Control: el test anterior sí puede fallar. Si se le pide que compare
    contra una imagen que el contenedor real no tiene, falla."""
    tags_reales = _tags_reales(postgres_contenedor)
    imagen_falsa = "postgres:1.0.0-no-existe"
    assert imagen_falsa not in tags_reales
