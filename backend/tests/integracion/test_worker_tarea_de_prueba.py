"""Tests de integración del worker en proceso (D2, D3, D8). Cambio 1c,
tarea 5.5.

`burst=True`, espera base 0,05 s (la de los tests, D3): corre contra Redis y
PostgreSQL reales de sesión (D12), hasta drenar la cola.

Escenarios de `cola-de-trabajos`: Tarea de prueba exitosa; Falla pasajera y
después éxito. Escenarios de `trazabilidad-y-logs`: Hasta el worker.
"""

import io
import json
import logging
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import arq
import arq.worker
import pytest
from sqlalchemy import text

from proptech_core.compartido.logs import FormateadorJSON
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import encolar_tarea_de_prueba

pytestmark = pytest.mark.integracion

_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)


def _capturar_logs() -> io.StringIO:
    """Redirige el handler de la raíz (configurado por `configurar_logs` al
    importar `proptech_worker.ajustes`, D7) a un buffer propio del test."""
    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        if isinstance(handler.formatter, FormateadorJSON):
            handler.stream = salida  # type: ignore[attr-defined]
    return salida


def _lineas_json(salida: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]


async def _correr_worker_burst(
    ajustes_del_worker: Any, nombre_cola: str, *, max_burst_jobs: int = 10
) -> None:
    # El tipo declarado por `arq.worker.get_kwargs` (`dict[str, NameError]`)
    # es un error de sus propios stubs: en runtime son los atributos de
    # `AjustesDelWorker`, de los tipos que pide `arq.Worker.__init__`.
    kwargs: dict[str, Any] = dict(arq.worker.get_kwargs(ajustes_del_worker.AjustesDelWorker))

    async def _on_startup_de_test(ctx: dict[str, Any]) -> None:
        await ajustes_del_worker.on_startup(ctx)
        # Espera base rápida (D3): los tests no esperan 2, 4, 8, 16 s reales.
        ctx["politica"] = _POLITICA_RAPIDA

    kwargs["on_startup"] = _on_startup_de_test
    # Cola propia (L-006, mismo espíritu que un contenedor propio): sin esto,
    # un burst también drena trabajos huérfanos de otros tests que comparten
    # el mismo Redis de sesión (p.ej. `test_cola.py`, que nunca corre un
    # worker) y contamina los conteos de eventos de este test.
    kwargs["queue_name"] = nombre_cola
    worker = arq.Worker(
        **kwargs,
        burst=True,
        handle_signals=False,
        poll_delay=0.01,
        max_burst_jobs=max_burst_jobs,
    )
    try:
        await worker.async_run()
    finally:
        await worker.close()


def _fila(ajustes_del_worker: Any, clave: str) -> Any:
    from proptech_core.compartido.base_de_datos import crear_engine

    engine = crear_engine(ajustes_del_worker._configuracion)
    try:
        with engine.connect() as conexion:
            return conexion.execute(
                text("SELECT tarea, request_id FROM trabajos_hechos WHERE clave = :clave"),
                {"clave": clave},
            ).first()
    finally:
        engine.dispose()


@pytest.mark.anyio
async def test_cero_fallas_registra_la_clave_en_un_intento(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    clave = f"worker-{uuid.uuid4()}"
    request_id = str(uuid.uuid4())
    await encolar_tarea_de_prueba(cola, clave=clave, request_id=request_id, fallar_veces=0)
    salida = _capturar_logs()
    await _correr_worker_burst(ajustes_del_worker, nombre_cola)

    fila = _fila(ajustes_del_worker, clave)
    assert fila is not None
    assert fila[0] == "tarea_de_prueba"
    assert str(fila[1]) == request_id

    lineas = _lineas_json(salida)
    assert not any(linea["evento"] == "reintento_programado" for linea in lineas)
    assert not any(linea["evento"] == "tarea_agotada" for linea in lineas)


@pytest.mark.anyio
async def test_dos_fallas_tres_intentos_y_una_sola_fila(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    clave = f"worker-{uuid.uuid4()}"
    request_id = str(uuid.uuid4())
    await encolar_tarea_de_prueba(cola, clave=clave, request_id=request_id, fallar_veces=2)
    salida = _capturar_logs()
    await _correr_worker_burst(ajustes_del_worker, nombre_cola)

    fila = _fila(ajustes_del_worker, clave)
    assert fila is not None
    assert fila[0] == "tarea_de_prueba"

    lineas = _lineas_json(salida)
    reintentos = [linea for linea in lineas if linea["evento"] == "reintento_programado"]
    assert len(reintentos) == 2, lineas
    assert not any(linea["evento"] == "tarea_agotada" for linea in lineas)
    # Las dos líneas de reintento y la fila llevan el request_id con que se encoló.
    assert all(linea.get("request_id") == request_id for linea in reintentos)
    assert str(fila[1]) == request_id


@pytest.mark.anyio
async def test_request_id_invalido_se_reemplaza_y_se_loguea(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    clave = f"worker-{uuid.uuid4()}"
    await cola.encolar("tarea_de_prueba", clave=clave, request_id="no-es-un-uuid", fallar_veces=0)
    salida = _capturar_logs()
    await _correr_worker_burst(ajustes_del_worker, nombre_cola)

    fila = _fila(ajustes_del_worker, clave)
    assert fila is not None
    assert str(fila[1]) != "no-es-un-uuid"
    uuid.UUID(str(fila[1]))  # el reemplazo es un UUID válido

    lineas = _lineas_json(salida)
    assert any(linea["evento"] == "request_id_reemplazado" for linea in lineas)
    assert not any("no-es-un-uuid" in json.dumps(linea) for linea in lineas)


@pytest.mark.anyio
async def test_on_startup_usa_crear_engine_con_la_configuracion_del_pool(
    ajustes_del_worker: Any,
) -> None:
    """Gemelo de la tarea 3.6 (L-009, D18): el engine del worker toma de la
    configuración los mismos parámetros de pool que el de la API."""
    import proptech_worker.ajustes as ajustes_mod

    ctx: dict[str, Any] = {}
    with (
        patch.object(ajustes_mod, "crear_engine") as creado,
        patch.object(ajustes_mod, "crear_fabrica_de_sesiones") as fabrica_creada,
        patch.object(ajustes_mod, "registrar_application_name"),
        # D4, D8 (tarea 7.1): `on_startup` también registra el tenant sobre
        # la fábrica de sesiones; sin parchear esto, SQLAlchemy intenta
        # colgar un evento `after_begin` real de un `MagicMock()`.
        patch.object(ajustes_mod, "registrar_tenant_por_administracion"),
        # R7 (vuelta 2): mismo motivo, para el evento "checkin" del engine.
        patch.object(ajustes_mod, "registrar_reset_del_tenant_al_devolver"),
    ):
        creado.return_value = MagicMock()
        fabrica_creada.return_value = MagicMock()
        await ajustes_mod.on_startup(ctx)

    assert creado.call_count == 1
    args, kwargs = creado.call_args
    assert args[0] is ajustes_mod._configuracion
    assert kwargs["connect_args"] == {"application_name": "proptech-worker"}
