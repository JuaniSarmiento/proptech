"""Tests de `crear_engine`: toma los parámetros del pool de la configuración
(D18, M14). Cambio 1c, tarea 3.6 (parte 2 de 3)."""

from unittest.mock import MagicMock, patch

import pytest

import proptech_core.compartido.base_de_datos as base_de_datos_mod
from proptech_core.compartido.configuracion import Configuracion


def _configuracion(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Configuracion:
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "proptech")
    monkeypatch.setenv("POSTGRES_PASSWORD", "clave")
    monkeypatch.setenv("POSTGRES_DB", "proptech")
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_POOL_RECYCLE_S", "900")
    monkeypatch.setenv("DB_POOL_TIMEOUT_S", "11")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT_S", "4")
    for clave, valor in overrides.items():
        monkeypatch.setenv(clave, valor)
    return Configuracion()


def test_crear_engine_pasa_los_parametros_del_pool_de_la_configuracion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuracion = _configuracion(monkeypatch)

    with patch.object(base_de_datos_mod, "create_engine") as creado:
        creado.return_value = MagicMock()
        base_de_datos_mod.crear_engine(configuracion)

    assert creado.call_count == 1
    _, kwargs = creado.call_args
    assert kwargs["pool_pre_ping"] == configuracion.db_pool_pre_ping
    assert kwargs["pool_size"] == 7
    assert kwargs["pool_recycle"] == 900
    assert kwargs["pool_timeout"] == 11
    assert kwargs["connect_args"]["connect_timeout"] == 4


def test_connect_args_explicito_pisa_el_connect_timeout_de_la_configuracion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuracion = _configuracion(monkeypatch)

    with patch.object(base_de_datos_mod, "create_engine") as creado:
        creado.return_value = MagicMock()
        base_de_datos_mod.crear_engine(configuracion, connect_args={"connect_timeout": 99})

    _, kwargs = creado.call_args
    assert kwargs["connect_args"]["connect_timeout"] == 99
