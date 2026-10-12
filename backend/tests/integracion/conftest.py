"""Valores de entorno por defecto para los tests de integración.

`Configuracion()` (D11) exige también las variables de Redis y
`PROPTECH_PARAMETROS`, aunque el test sólo le interese PostgreSQL (p.ej. Alembic
o el verificador de salud). Un test puede pisar cualquiera con su propio
`monkeypatch.setenv`/`delenv` para probar el caso contrario.
"""

from pathlib import Path

import pytest

_PARAMETROS_DEL_REPO = Path(__file__).resolve().parents[3] / "config" / "parametros.yaml"


@pytest.fixture(autouse=True)
def _variables_ampliadas_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", "redis-pass")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(_PARAMETROS_DEL_REPO))
