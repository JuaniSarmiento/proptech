"""Ataque vuelta 2 (F2 cerrado a medias): con la sesión en `asyncio.to_thread`
el loop ya no se frena, pero con la base CONGELADA (no caída) el trabajo
nunca se trata como pasajero: vence `job_timeout`, ARQ lo da por fallado sin
reintento y sin `tarea_agotada` (el `TimeoutError` de `asyncio.wait_for` nace
afuera de `reintentable`). El hilo sigue colgado con la transacción abierta, y
cuando la base vuelve, confirma: la fila aparece para un trabajo que ARQ ya
marcó fallido."""

import io
import json
import logging
import threading
import time
import uuid
from typing import Any

import arq
import arq.worker
import pytest
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_application_name,
)
from proptech_core.compartido.logs import FormateadorJSON
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import NOMBRE_TAREA_DE_PRUEBA

from .test_worker_base_caida_durante_el_trabajo import (
    _configuracion_para,
    _migrar_a_head,
    contenedor_propio,  # noqa: F401  (fixture)
)

pytestmark = pytest.mark.integracion
_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)
_logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_base_congelada_durante_el_trabajo_se_reintenta_o_queda_agotada(
    ajustes_del_worker: Any,
    contenedor_propio: PostgresContainer,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    _migrar_a_head(contenedor_propio)
    configuracion_test = _configuracion_para(contenedor_propio, monkeypatch)
    engine = crear_engine(configuracion_test, connect_args={"application_name": "proptech-worker"})
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_application_name(fabrica, "proptech-worker")

    async def _on_startup_de_test(ctx: dict[str, Any]) -> None:
        ctx["engine"] = engine
        ctx["fabrica_de_sesiones"] = fabrica
        ctx["politica"] = _POLITICA_RAPIDA

    kwargs: dict[str, Any] = dict(arq.worker.get_kwargs(ajustes_del_worker.AjustesDelWorker))
    kwargs.update(
        on_startup=_on_startup_de_test, on_shutdown=None, queue_name=nombre_cola, job_timeout=2
    )

    # Conexión abierta en el pool.
    await cola.encolar(
        NOMBRE_TAREA_DE_PRUEBA,
        clave=f"a-{uuid.uuid4()}",
        request_id=str(uuid.uuid4()),
        fallar_veces=0,
    )
    w1 = arq.Worker(**kwargs, burst=True, handle_signals=False, poll_delay=0.01)
    await w1.async_run()
    await w1.close()

    salida = io.StringIO()
    for nombre in ("", "arq"):
        for handler in logging.getLogger(nombre).handlers:
            if isinstance(handler.formatter, FormateadorJSON):
                handler.stream = salida  # type: ignore[attr-defined]

    clave = f"b-{uuid.uuid4()}"
    contenedor = contenedor_propio.get_wrapped_container()
    contenedor.pause()
    red = threading.Timer(20, contenedor.unpause)
    red.start()
    try:
        await cola.encolar(
            NOMBRE_TAREA_DE_PRUEBA, clave=clave, request_id=str(uuid.uuid4()), fallar_veces=0
        )
        w2 = arq.Worker(
            **kwargs, burst=True, handle_signals=False, poll_delay=0.01, max_burst_jobs=1
        )
        await w2.async_run()
        await w2.close()
    finally:
        red.cancel()
        try:
            contenedor.unpause()
        except Exception:
            _logger.exception("no se pudo despausar el contenedor propio del test")

    time.sleep(1.5)  # el hilo colgado termina su INSERT y su COMMIT
    with engine.connect() as conexion:
        fila = conexion.execute(
            text("SELECT 1 FROM trabajos_hechos WHERE clave = :c"), {"c": clave}
        ).first()
    engine.dispose()

    eventos = [
        json.loads(linea).get("evento") for linea in salida.getvalue().splitlines() if linea.strip()
    ]
    tratado_como_pasajero = "reintento_programado" in eventos or "tarea_agotada" in eventos
    assert tratado_como_pasajero, (
        f"base congelada: ni reintento ni tarea_agotada (eventos={eventos}); "
        f"fila registrada igual después del fallo: {fila is not None}"
    )
