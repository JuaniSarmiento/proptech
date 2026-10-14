"""Ataque vuelta 3 (F2b/F2c): la cota de 1,5 s levanta `TimeoutError` en la
corrutina, pero el hilo colgado sigue con su transacción. Si la base sigue
congelada más que todos los reintentos, el trabajo queda `tarea_agotada`; al
volver la base, el hilo del primer intento confirma: efecto aplicado con el
trabajo marcado agotado.

Marcado `xfail(strict=True)` a propósito (cierre de la vuelta 3, veredicto del
auditor + decisión de Juani): es una LIMITACIÓN CONOCIDA del cambio 1c,
documentada en `proptech_worker/tareas.py` (comentario de `COTA_OPERACION_S` y
el de `tarea_de_prueba`), no un defecto que se arregle acá. Tolerable en 1c
porque el efecto de `tarea_de_prueba` es vacío; el cambio 7 (primera tarea con
efecto real) tiene que resolverlo con un corte del lado de la base
(`statement_timeout`/`lock_timeout`) y una cota propia por tarea antes de
registrar esa tarea. Si este test empieza a pasar solo, algo cambió el
comportamiento y hay que revisar si la limitación se cerró de verdad o si el
`xfail` quedó obsoleto por otro motivo.
"""

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
@pytest.mark.xfail(
    strict=True,
    reason=(
        "F2c: deuda del cambio 7 (documentada en tareas.py) — el hilo del primer "
        "intento puede confirmar su efecto después de que ARQ ya marcó el trabajo "
        "tarea_agotada, porque asyncio.wait_for corta la espera, no el hilo."
    ),
)
async def test_trabajo_agotado_por_base_congelada_no_deja_efecto_despues(
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
    kwargs.update(on_startup=_on_startup_de_test, on_shutdown=None, queue_name=nombre_cola)

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
    red = threading.Timer(60, contenedor.unpause)
    red.start()
    try:
        await cola.encolar(
            NOMBRE_TAREA_DE_PRUEBA, clave=clave, request_id=str(uuid.uuid4()), fallar_veces=0
        )
        w2 = arq.Worker(
            **kwargs, burst=True, handle_signals=False, poll_delay=0.01, max_burst_jobs=10
        )
        await w2.async_run()
        await w2.close()
        hilos_vivos = threading.active_count()
    finally:
        red.cancel()
        try:
            contenedor.unpause()
        except Exception:
            _logger.exception("no se pudo despausar el contenedor propio del test")

    time.sleep(3)
    with engine.connect() as conexion:
        fila = conexion.execute(
            text("SELECT 1 FROM trabajos_hechos WHERE clave = :c"), {"c": clave}
        ).first()
    engine.dispose()

    eventos = [
        json.loads(linea).get("evento") for linea in salida.getvalue().splitlines() if linea.strip()
    ]
    print("EVENTOS", [e for e in eventos if not e.startswith("%") and "redis_version" not in e])
    print("HILOS_VIVOS_CON_BASE_CONGELADA", hilos_vivos)
    assert "tarea_agotada" in eventos, f"eventos={eventos}"
    assert fila is None, (
        "trabajo marcado tarea_agotada y su efecto quedó aplicado al volver la base"
    )
