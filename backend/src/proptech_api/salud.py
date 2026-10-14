"""Endpoint de salud: informa si el sistema, la base y la cola responden
(D11, D18, D4)."""

import logging
import queue
import threading
from collections.abc import Callable

import redis
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.engine import Engine

from proptech_core.compartido.conexion_redis import cliente_redis_sincrono
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.logs import datos_de_excepcion

#: Prefijo fijado en el propio router (no al incluirlo en `crear_app()`):
#: en esta versión de FastAPI el prefijo pasado a `include_router(prefix=...)`
#: no queda en `path_format` de la ruta que termina en `scope["route"]` (F3,
#: vuelta 2 de 1c); fijado acá, `path_format` ya lo trae desde que se define.
router = APIRouter(prefix="/api")

_logger = logging.getLogger("proptech_api.salud")

#: Plazo propio de la verificación (D18), aparte del `connect_timeout` del
#: engine: cubre también una conexión ya abierta en el pool que se congela
#: después (el `connect_timeout` sólo acota el establecimiento inicial).
PLAZO_VERIFICACION_S = 2.0


def _verificador_con_engine(engine: Engine) -> Callable[[], bool]:
    """Fábrica del verificador real: corre el `SELECT 1` en un hilo propio
    con un plazo fijo, así una conexión congelada (D18) no cuelga el pedido.
    Ante cualquier falla, loguea `salud_degradada` con `dependencia` y
    `tipo_error`, nunca el mensaje de psycopg (L-007)."""

    def _verificar() -> bool:
        resultado: queue.Queue[bool] = queue.Queue(maxsize=1)

        def _trabajo() -> None:
            try:
                with engine.connect() as conexion:
                    conexion.execute(text("SELECT 1"))
                resultado.put(True)
            except Exception as error:
                _logger.error(
                    "salud_degradada",
                    extra={"dependencia": "base", **datos_de_excepcion(error)},
                )
                resultado.put(False)

        hilo = threading.Thread(target=_trabajo, daemon=True)
        hilo.start()
        try:
            return resultado.get(timeout=PLAZO_VERIFICACION_S)
        except queue.Empty:
            # El hilo sigue colgado (conexión congelada): no esperamos más.
            # La conexión que tomó del pool queda sin devolver; `pool_timeout`
            # acota cuánto esperan los próximos pedidos si esto se repite.
            _logger.error(
                "salud_degradada",
                extra={"dependencia": "base", "tipo_error": "TimeoutError"},
            )
            return False

    return _verificar


def obtener_verificador_de_base(request: Request) -> Callable[[], bool]:
    """Dependencia de FastAPI, inyectable: devuelve el verificador contra el
    único engine del proceso (`app.state.engine`, creado en el lifespan de
    `crear_app()`, D18)."""
    return _verificador_con_engine(request.app.state.engine)


def _verificador_con_cliente_redis(cliente: redis.Redis) -> Callable[[], bool]:
    """Fábrica del verificador de cola (D4, D18, gemelo de
    `_verificador_con_engine`, L-009): `socket_connect_timeout`/
    `socket_timeout` (fijados al crear el cliente,
    `conexion_redis.cliente_redis_sincrono`) acotan cada OPERACIÓN por
    separado, no el total; con Redis lento (cada comando responde por debajo
    de ese timeout) el cliente manda varios comandos antes del `PING`
    (`AUTH`, `CLIENT SETINFO` x2) y la verificación completa tarda varias
    veces ese plazo. Por eso corre en un hilo propio con un plazo TOTAL fijo
    (`PLAZO_VERIFICACION_S`), igual que el verificador de base. Cualquier
    excepción o el vencimiento del plazo es `sin_conexion`; se loguea
    `salud_degradada` con `dependencia: cola` y el tipo de error, nunca el
    mensaje de redis-py (L-007)."""

    def _verificar() -> bool:
        resultado: queue.Queue[bool] = queue.Queue(maxsize=1)

        def _trabajo() -> None:
            try:
                cliente.ping()
                resultado.put(True)
            except Exception as error:
                _logger.error(
                    "salud_degradada",
                    extra={"dependencia": "cola", **datos_de_excepcion(error)},
                )
                resultado.put(False)

        hilo = threading.Thread(target=_trabajo, daemon=True)
        hilo.start()
        try:
            return resultado.get(timeout=PLAZO_VERIFICACION_S)
        except queue.Empty:
            # El hilo sigue colgado (Redis lento o congelado más allá del
            # plazo total): no esperamos más.
            _logger.error(
                "salud_degradada",
                extra={"dependencia": "cola", "tipo_error": "TimeoutError"},
            )
            return False

    return _verificar


def obtener_verificador_de_cola(request: Request) -> Callable[[], bool]:
    """Dependencia de FastAPI, inyectable: a diferencia del engine de base de
    datos (D18), el cliente síncrono de Redis no mantiene un pool caro de
    reutilizar, así que se crea uno nuevo por pedido a partir de la
    configuración (sin necesitar que `crear_app()` lo cablee en `app.state`)."""
    return _verificador_con_cliente_redis(cliente_redis_sincrono(Configuracion()))


@router.get("/salud")
def salud(
    response: Response,
    verificador_base: Callable[[], bool] = Depends(obtener_verificador_de_base),
    verificador_cola: Callable[[], bool] = Depends(obtener_verificador_de_cola),
) -> dict[str, str]:
    try:
        base_responde = verificador_base()
    except Exception:
        base_responde = False

    try:
        cola_responde = verificador_cola()
    except Exception:
        cola_responde = False

    cuerpo = {
        "estado": "ok" if base_responde and cola_responde else "degradado",
        "base": "ok" if base_responde else "sin_conexion",
        "cola": "ok" if cola_responde else "sin_conexion",
    }
    if not (base_responde and cola_responde):
        response.status_code = 503
    return cuerpo
