"""Ataque del rompedor (vuelta 2, F2; L-001, D2): la base se CONGELA con una
conexión ya abierta en el pool del worker. D2 dice que el trabajo de base
corre con `asyncio.to_thread`; `tarea_de_prueba` abría la sesión síncrona
directo en el event loop, así que un `SELECT` colgado (el `pool_pre_ping`
sobre la conexión congelada) frenaba todo el loop: ni `job_timeout` ni el
health check de ARQ podían correr.
"""

import asyncio
import threading
import time
import uuid
from contextlib import suppress
from typing import Any

import arq
import arq.worker
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_application_name,
)
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import NOMBRE_TAREA_DE_PRUEBA

from .test_worker_base_caida_durante_el_trabajo import (
    _configuracion_para,
    _migrar_a_head,
    contenedor_propio,  # noqa: F401  (fixture)
)

pytestmark = pytest.mark.integracion

_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)
#: Cuánto puede quedar frenado el event loop del worker con la base congelada.
_MAXIMO_LOOP_FRENADO_S = 3.0
#: Red de seguridad del test: despausa sí o sí a los 12 s.
_DESPAUSAR_A_LOS_S = 12.0


@pytest.mark.anyio
async def test_base_congelada_con_conexion_abierta_no_frena_el_loop_del_worker(
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
    kwargs["on_startup"] = _on_startup_de_test
    kwargs["on_shutdown"] = None
    kwargs["queue_name"] = nombre_cola
    kwargs["job_timeout"] = 2

    # 1) Un trabajo normal deja una conexión abierta en el pool.
    await cola.encolar(
        NOMBRE_TAREA_DE_PRUEBA,
        clave=f"a-{uuid.uuid4()}",
        request_id=str(uuid.uuid4()),
        fallar_veces=0,
    )
    w1 = arq.Worker(**kwargs, burst=True, handle_signals=False, poll_delay=0.01)
    await w1.async_run()
    await w1.close()
    assert engine.pool.checkedin() >= 1  # type: ignore[attr-defined]

    # 2) Se congela la base con esa conexión abierta y se encola otro trabajo.
    contenedor = contenedor_propio.get_wrapped_container()
    contenedor.pause()
    temporizador = threading.Timer(_DESPAUSAR_A_LOS_S, contenedor.unpause)
    temporizador.start()
    await cola.encolar(
        NOMBRE_TAREA_DE_PRUEBA,
        clave=f"b-{uuid.uuid4()}",
        request_id=str(uuid.uuid4()),
        fallar_veces=0,
    )

    huecos: list[float] = []
    terminado = asyncio.Event()

    async def _latido() -> None:
        anterior = time.monotonic()
        while not terminado.is_set():
            await asyncio.sleep(0.1)
            ahora = time.monotonic()
            huecos.append(ahora - anterior)
            anterior = ahora

    latido = asyncio.ensure_future(_latido())
    w2 = arq.Worker(**kwargs, burst=True, handle_signals=False, poll_delay=0.01, max_burst_jobs=1)
    try:
        await w2.async_run()
    finally:
        terminado.set()
        await latido
        temporizador.cancel()
        with suppress(Exception):
            contenedor.unpause()
        await w2.close()
        engine.dispose()

    assert max(huecos) < _MAXIMO_LOOP_FRENADO_S, (
        f"el event loop del worker quedó frenado {max(huecos):.1f}s con la base congelada"
    )
