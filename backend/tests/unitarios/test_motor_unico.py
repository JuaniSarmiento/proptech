"""Tests del engine único por proceso (D18, M13). Cambio 1c, tarea 3.6
(parte 3 de 3).

Escenarios de `entorno-de-ejecucion`: Un solo engine por proceso; La base no
responde. Lecciones: L-001, L-002, L-007.
"""

import io
import json
import logging
import socket
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _puerto_libre_sin_servidor() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_el_lifespan_crea_un_solo_engine_y_lo_descarta_al_cerrar() -> None:
    # La fábrica valida `Configuracion()` al llamarla; el fixture autouse
    # ya puso las variables de entorno por defecto antes de crear la app.
    import proptech_api.app as app_mod
    from proptech_api import salud as salud_mod

    motor_falso = MagicMock()
    with (
        patch.object(app_mod, "crear_engine", return_value=motor_falso) as espia,
        # R7 (vuelta 2): `registrar_reset_del_tenant_al_devolver` cuelga un
        # evento "checkin" real del ENGINE; un `MagicMock()` no es un target
        # de evento de SQLAlchemy válido.
        patch.object(app_mod, "registrar_reset_del_tenant_al_devolver"),
        # R8 (vuelta 2): `verificar_rol_de_aplicacion_seguro` desempaqueta
        # una fila real de 3 columnas; un `MagicMock()` no la da.
        patch.object(app_mod, "verificar_rol_de_aplicacion_seguro"),
    ):
        app = app_mod.crear_app()
        with TestClient(app) as cliente:
            app.dependency_overrides[salud_mod.obtener_verificador_de_base] = lambda: lambda: True
            cliente.get("/api/salud")
            assert espia.call_count == 1
            assert app.state.engine is motor_falso
            motor_falso.dispose.assert_not_called()

    motor_falso.dispose.assert_called_once()


def test_diez_pedidos_a_salud_no_crean_engines_nuevos() -> None:
    import proptech_api.app as app_mod
    from proptech_api import salud as salud_mod

    motor_falso = MagicMock()
    with (
        patch.object(app_mod, "crear_engine", return_value=motor_falso) as espia,
        patch.object(app_mod, "registrar_reset_del_tenant_al_devolver"),
        patch.object(app_mod, "verificar_rol_de_aplicacion_seguro"),
    ):
        app = app_mod.crear_app()
        app.dependency_overrides[salud_mod.obtener_verificador_de_base] = lambda: lambda: True
        # 4.6 agrega el verificador de cola al mismo endpoint: sin overridearlo,
        # intenta un PING real a REDIS_HOST=redis (no resuelve en este test).
        app.dependency_overrides[salud_mod.obtener_verificador_de_cola] = lambda: lambda: True
        with TestClient(app) as cliente:
            for _ in range(10):
                respuesta = cliente.get("/api/salud")
                assert respuesta.status_code == 200

    assert espia.call_count == 1


def test_base_no_responde_devuelve_false_y_loguea_salud_degradada_sin_el_mensaje() -> None:
    from sqlalchemy import create_engine

    from proptech_api.salud import _verificador_con_engine
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        handler.stream = salida  # type: ignore[attr-defined]

    puerto = _puerto_libre_sin_servidor()
    engine = create_engine(
        f"postgresql+psycopg://u:p@127.0.0.1:{puerto}/db",
        connect_args={"connect_timeout": 2},
    )
    try:
        verificar = _verificador_con_engine(engine)
        inicio = time.monotonic()
        assert verificar() is False
        assert time.monotonic() - inicio < 5
    finally:
        engine.dispose()

    eventos = [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]
    degradados = [e for e in eventos if e.get("evento") == "salud_degradada"]
    assert len(degradados) == 1
    assert degradados[0]["dependencia"] == "base"
    assert degradados[0]["tipo_error"]
    assert "Connection refused" not in salida.getvalue()
    assert str(puerto) not in salida.getvalue()


@pytest.mark.parametrize("variable", ["DB_POOL_SIZE"])
def test_configuracion_pool_sigue_rechazando_valores_invalidos_al_crear_app(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    """Regresión mínima: `crear_app()` sigue fallando rápido si un parámetro
    del pool viene roto (mismo mecanismo de `ConfiguracionInvalida` de 3.5)."""
    from proptech_api.app import crear_app
    from proptech_core.compartido.configuracion import ConfiguracionInvalida

    monkeypatch.setenv(variable, "no-es-un-numero")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        crear_app()

    assert variable in str(exc_info.value)
