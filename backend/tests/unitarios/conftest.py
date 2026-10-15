"""Valores de entorno por defecto para los tests unitarios.

Ninguno de estos tests habla con una base real, pero construir la app (D11:
`Configuracion()` se valida al crear la app, no recién al primer pedido) exige
una `Configuracion` válida. Un test puede pisar cualquiera de estas variables
con su propio `monkeypatch.setenv`/`delenv` para probar el caso contrario.
"""

from pathlib import Path

import pytest

_PARAMETROS_DEL_REPO = Path(__file__).resolve().parents[3] / "config" / "parametros.yaml"


@pytest.fixture(autouse=True)
def _variables_de_postgres_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "proptech")
    # Rol de arranque (D1): el superusuario de la imagen. Lo usa `roles.py`.
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", "proptech")
    # Rol del migrador (D1, D3): corre Alembic. Lo usa `migraciones/env.py`.
    monkeypatch.setenv("POSTGRES_MIGRADOR_USER", "proptech_migrador")
    monkeypatch.setenv("POSTGRES_MIGRADOR_PASSWORD", "proptech_migrador")
    # Rol de la app (D1, D3): lo usan `Configuracion()`, la API y el worker.
    monkeypatch.setenv("POSTGRES_APP_USER", "proptech_app")
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", "proptech_app")
    # Rol de respaldo (D1, D3): sólo lo valida esta `Configuracion`-hermana en tests.
    monkeypatch.setenv("POSTGRES_RESPALDO_USER", "proptech_respaldo")
    monkeypatch.setenv("POSTGRES_RESPALDO_PASSWORD", "proptech_respaldo")
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", "redis-pass")
    # El archivo real del repositorio (D6/D-042): válido de punta a punta, así
    # crear_app() (que ahora llama a leer_parametros) no falla por default.
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(_PARAMETROS_DEL_REPO))
