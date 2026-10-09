"""Valores de entorno por defecto para los tests unitarios.

Ninguno de estos tests habla con una base real, pero construir la app (D11:
`Configuracion()` se valida al crear la app, no recién al primer pedido) exige
una `Configuracion` válida. Un test puede pisar cualquiera de estas variables
con su propio `monkeypatch.setenv`/`delenv` para probar el caso contrario.
"""

import pytest


@pytest.fixture(autouse=True)
def _variables_de_postgres_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", "proptech")
    monkeypatch.setenv("POSTGRES_DB", "proptech")
