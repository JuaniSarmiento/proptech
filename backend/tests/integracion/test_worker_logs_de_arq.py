"""Test de integración del worker en proceso sobre los logs de ARQ (D7, M25).
Cambio 1c, tarea 5.7.

ARQ, por defecto, escribe los argumentos y el resultado de cada trabajo en
`arq.worker`/`arq.jobs` (nivel info). El formatter propio descarta
`record.args` (D7) y `AjustesDelWorker.log_results = False` es el segundo
candado.

Escenario de `trazabilidad-y-logs`: Argumentos y resultado de un trabajo.
Lecciones: L-007.
"""

import io
import json
import logging
import uuid
from typing import Any

import arq
import arq.worker
import pytest

from proptech_core.compartido.logs import FormateadorJSON
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import NOMBRE_TAREA_DE_PRUEBA

pytestmark = pytest.mark.integracion

_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)


async def _tarea_con_resultado_marcado(
    ctx: dict[str, Any], *, request_id: str, clave: str, resultado_marcado: str
) -> str:
    return resultado_marcado


def _capturar_logs() -> io.StringIO:
    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        if isinstance(handler.formatter, FormateadorJSON):
            handler.stream = salida  # type: ignore[attr-defined]
    return salida


@pytest.mark.anyio
async def test_logs_de_arq_no_dejan_el_argumento_ni_el_resultado_marcados(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    marcador_arg = f"marcador-argumento-{uuid.uuid4().hex[:12]}"
    marcador_resultado = f"marcador-resultado-{uuid.uuid4().hex[:12]}"

    kwargs: dict[str, Any] = dict(arq.worker.get_kwargs(ajustes_del_worker.AjustesDelWorker))
    kwargs["functions"] = [*kwargs["functions"], _tarea_con_resultado_marcado]
    kwargs["queue_name"] = nombre_cola

    async def _on_startup_de_test(ctx: dict[str, Any]) -> None:
        await ajustes_del_worker.on_startup(ctx)
        ctx["politica"] = _POLITICA_RAPIDA

    kwargs["on_startup"] = _on_startup_de_test

    clave_tarea_de_prueba = f"worker-logs-arq-{uuid.uuid4()}"
    await cola.encolar(
        NOMBRE_TAREA_DE_PRUEBA,
        clave=clave_tarea_de_prueba,
        request_id=str(uuid.uuid4()),
        fallar_veces=0,
        dato_extra_marcado=marcador_arg,
    )
    await cola.encolar(
        "_tarea_con_resultado_marcado",
        clave=f"worker-logs-arq-resultado-{uuid.uuid4()}",
        request_id=str(uuid.uuid4()),
        resultado_marcado=marcador_resultado,
    )

    salida = _capturar_logs()
    worker = arq.Worker(
        **kwargs, burst=True, handle_signals=False, poll_delay=0.01, max_burst_jobs=10
    )
    try:
        await worker.async_run()
    finally:
        await worker.close()

    # El trabajo con el argumento extra marcado tiene que haber corrido de
    # verdad (D2: `**datos` acepta cualquier argumento extra sin fallar), no
    # sólo "no haber dejado el marcador" porque falló antes de loguear nada.
    from sqlalchemy import text

    from proptech_core.compartido.base_de_datos import crear_engine

    engine = crear_engine(ajustes_del_worker._configuracion)
    try:
        with engine.connect() as conexion:
            fila = conexion.execute(
                text("SELECT clave FROM trabajos_hechos WHERE clave = :clave"),
                {"clave": clave_tarea_de_prueba},
            ).first()
    finally:
        engine.dispose()
    assert fila is not None, "la tarea con el argumento extra no completó (¿rechazó **datos?)"

    texto = salida.getvalue()
    lineas = [json.loads(linea) for linea in texto.splitlines() if linea.strip()]
    assert marcador_arg not in texto
    assert marcador_resultado not in texto
    assert marcador_arg not in json.dumps(lineas)
    assert marcador_resultado not in json.dumps(lineas)
