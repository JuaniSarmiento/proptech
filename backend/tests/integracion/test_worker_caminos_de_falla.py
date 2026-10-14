"""Tests de integración del worker en proceso, caminos de falla (D2, D3, D7).
Cambio 1c, tarea 5.6.

Escenarios de `cola-de-trabajos`: Intentos agotados; Trabajo con formato
ajeno. Escenarios de `trazabilidad-y-logs`: Error de un tercero con datos en
su mensaje (caso de ARQ, que no entra en la tarea 2.2). Lecciones: L-007.
"""

import io
import json
import logging
import pickle
import time
import uuid
from typing import Any

import arq
import arq.worker
import pytest
import redis.asyncio as redis_asincronico
from arq.jobs import SerializationError

from proptech_core.compartido.logs import FormateadorJSON, datos_de_excepcion
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import encolar_tarea_de_prueba

pytestmark = pytest.mark.integracion

_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)
MARCADOR = "marcador-formato-ajeno-6d19af"


def _capturar_logs() -> io.StringIO:
    """Redirige el handler propio de la raíz Y del logger `arq` (D7): el
    rechazo de un trabajo con formato ajeno lo loguea `arq.worker`
    (`logger.exception('deserializing job %s failed', ...)`), que propaga
    hasta el handler de `arq` (su propio `StreamHandler`, no el de la
    raíz: `configurar_logs` le pone uno separado); sin redirigir también
    ése, ese evento se escribía en el stdout real y la aserción de la 5.6
    sobre su presencia nunca podía verlo (vuelta 2, F11)."""
    salida = io.StringIO()
    for nombre in ("", "arq"):
        for handler in logging.getLogger(nombre).handlers:
            if isinstance(handler.formatter, FormateadorJSON):
                handler.stream = salida  # type: ignore[attr-defined]
    return salida


def _lineas_json(salida: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]


async def _correr_worker_burst(
    ajustes_del_worker: Any, nombre_cola: str, *, max_burst_jobs: int = 10
) -> None:
    kwargs: dict[str, Any] = dict(arq.worker.get_kwargs(ajustes_del_worker.AjustesDelWorker))

    async def _on_startup_de_test(ctx: dict[str, Any]) -> None:
        await ajustes_del_worker.on_startup(ctx)
        ctx["politica"] = _POLITICA_RAPIDA

    kwargs["on_startup"] = _on_startup_de_test
    # Cola propia (L-006): ver el mismo comentario en test_worker_tarea_de_prueba.py.
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
    from sqlalchemy import text

    from proptech_core.compartido.base_de_datos import crear_engine

    engine = crear_engine(ajustes_del_worker._configuracion)
    try:
        with engine.connect() as conexion:
            return conexion.execute(
                text("SELECT clave FROM trabajos_hechos WHERE clave = :clave"),
                {"clave": clave},
            ).first()
    finally:
        engine.dispose()


@pytest.mark.anyio
async def test_cinco_fallas_cinco_intentos_tarea_agotada_y_ninguna_fila(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    clave = f"worker-falla-{uuid.uuid4()}"
    request_id = str(uuid.uuid4())
    # Con fallar_veces >= intentos_maximos (5), los cinco intentos fallan.
    await encolar_tarea_de_prueba(cola, clave=clave, request_id=request_id, fallar_veces=10)
    salida = _capturar_logs()
    await _correr_worker_burst(ajustes_del_worker, nombre_cola)

    assert _fila(ajustes_del_worker, clave) is None

    lineas = _lineas_json(salida)
    reintentos = [linea for linea in lineas if linea["evento"] == "reintento_programado"]
    agotados = [linea for linea in lineas if linea["evento"] == "tarea_agotada"]
    assert len(reintentos) == 4, lineas  # 4 reintentos + el 5to intento agotado = 5
    assert len(agotados) == 1, lineas
    assert agotados[0]["nivel"] == "error"
    assert agotados[0]["intento"] == 5


@pytest.mark.anyio
async def test_trabajo_con_pickle_no_se_ejecuta_y_no_deja_el_marcador(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, _cola = cola_de_prueba_aislada
    ajustes = ajustes_del_worker.AjustesDelWorker
    cliente = redis_asincronico.Redis(
        host=ajustes.redis_settings.host,
        port=ajustes.redis_settings.port,
        password=ajustes.redis_settings.password,
    )
    job_id = f"worker-pickle-{uuid.uuid4()}"
    try:
        crudo = pickle.dumps(
            {
                "f": "tarea_de_prueba",
                "a": (),
                "k": {
                    "request_id": str(uuid.uuid4()),
                    "clave": job_id,
                    "fallar_veces": 0,
                    "dato_marcado": MARCADOR,
                },
                "t": None,
                "et": int(time.time() * 1000),
            }
        )
        await cliente.psetex(f"arq:job:{job_id}", 60_000, crudo)
        await cliente.zadd(nombre_cola, {job_id: int(time.time() * 1000)})

        salida = _capturar_logs()
        await _correr_worker_burst(ajustes_del_worker, nombre_cola)

        assert _fila(ajustes_del_worker, job_id) is None

        lineas = _lineas_json(salida)
        assert MARCADOR not in salida.getvalue()
        assert MARCADOR not in json.dumps(lineas)
        # F11 (vuelta 2, JUICIO del rompedor; la spec lo pide con MUST): el
        # rechazo tiene que quedar registrado en el log, no sólo "no dejó
        # fila ni marcador". ARQ lo loguea por su cuenta
        # (`logger.exception('deserializing job %s failed', job_id)`,
        # `arq/worker.py`): el evento es su propia plantilla (sin el
        # contenido crudo del trabajo rechazado) y el nivel es de error.
        assert any("deserializing job" in str(linea.get("evento", "")) for linea in lineas), (
            f"el rechazo no quedó logueado: {lineas}"
        )
        assert any(linea.get("nivel") == "error" for linea in lineas), lineas
    finally:
        await cliente.aclose()


def test_error_real_de_arq_con_marcador_no_aparece_en_datos_de_excepcion() -> None:
    """Caso de ARQ que no entra en la tarea 2.2 (que cubrió psycopg) ni en la
    4.4 (redis-py): `arq.jobs.SerializationError`, la misma excepción que
    dispara el camino de "formato ajeno" de arriba."""
    marcador = "marcador-error-arq-2f7c91"
    try:
        raise SerializationError(f"no se pudo deserializar: {marcador}")
    except SerializationError as error:
        datos = datos_de_excepcion(error)
    serializado = json.dumps(datos)
    assert marcador not in serializado
    tipo_error = datos["tipo_error"]
    assert isinstance(tipo_error, str)
    assert tipo_error.endswith("SerializationError")
