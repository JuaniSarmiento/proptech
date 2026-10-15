"""Endpoint de salud: informa si el sistema, la base y la cola responden
(D11, D18, D4)."""

import contextvars
import logging
import queue
import threading
import time
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

#: Plazo TOTAL compartido entre la verificación de base y la de cola (D20,
#: F13): reemplaza el plazo de 2 s que tenía cada verificación por separado.
#: Con las dos corriendo en paralelo (`_ejecutar_verificaciones_en_paralelo`),
#: la respuesta llega dentro de este plazo aunque las dos estén congeladas,
#: en vez de la SUMA de los dos plazos (el bug que `/salud-web`, que corta a
#: 2 s, veía como "sin_conexion" con la API degradada pero contestando, F13).
PLAZO_TOTAL_SALUD_S = 1.5


def _informar_una_sola_vez(
    lock: threading.Lock,
    informado: list[bool],
    dependencia: str,
    datos_error: dict[str, object] | None,
) -> None:
    """Loguea `salud_degradada` para `dependencia` sólo la primera vez que se
    la llama entre quienes comparten el mismo `lock`/`informado` (D20): el
    plazo vencido y el hilo que termina tarde con un error compiten por
    informar, y sólo el primero que llega escribe la línea. El resto no
    escribe nada, ni siquiera el tipo de error (L-007: nunca el mensaje del
    driver de todos modos)."""
    with lock:
        if informado[0]:
            return
        informado[0] = True
    _logger.error(
        "salud_degradada",
        extra={"dependencia": dependencia, **(datos_error or {"tipo_error": "TimeoutError"})},
    )


def _verificador_con_engine(engine: Engine) -> Callable[[], bool]:
    """Fábrica del verificador real: corre el `SELECT 1` en un hilo propio
    con un plazo fijo, así una conexión congelada (D18) no cuelga el pedido.
    Ante cualquier falla, loguea `salud_degradada` con `dependencia` y
    `tipo_error`, nunca el mensaje de psycopg (L-007), exactamente una vez
    aunque el hilo termine después de vencido el plazo (D20)."""

    def _verificar() -> bool:
        resultado: queue.Queue[bool] = queue.Queue(maxsize=1)
        lock = threading.Lock()
        informado = [False]

        def _trabajo() -> None:
            try:
                with engine.connect() as conexion:
                    conexion.execute(text("SELECT 1"))
                resultado.put(True)
            except Exception as error:
                # Informa (loguea) ANTES de poner el resultado en la cola: si
                # el orden fuera al revés, el hilo principal podría despertar
                # de `resultado.get()` y devolver el resultado antes de que
                # esta línea se escriba (carrera que el test de regresión
                # `test_motor_unico.py` detectó).
                _informar_una_sola_vez(lock, informado, "base", datos_de_excepcion(error))
                resultado.put(False)

        # `context=contextvars.copy_context()` (B1, L-015): un `threading.Thread`
        # pelado NO hereda la `ContextVar` `request_id_actual` (Python 3.14 con
        # GIL, `sys.flags.thread_inherit_context == 0`), así que sin esto
        # cualquier línea `salud_degradada` logueada por este hilo (o por el
        # hilo de afuera que lo espera, ver `_ejecutar_verificaciones_en_paralelo`)
        # perdería el `request_id` del pedido en curso.
        hilo = threading.Thread(target=_trabajo, daemon=True, context=contextvars.copy_context())
        hilo.start()
        try:
            return resultado.get(timeout=PLAZO_TOTAL_SALUD_S)
        except queue.Empty:
            # El hilo sigue colgado (conexión congelada): no esperamos más.
            # La conexión que tomó del pool queda sin devolver; `pool_timeout`
            # acota cuánto esperan los próximos pedidos si esto se repite.
            _informar_una_sola_vez(lock, informado, "base", None)
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
    (`PLAZO_TOTAL_SALUD_S`), igual que el verificador de base. Cualquier
    excepción o el vencimiento del plazo es `sin_conexion`; se loguea
    `salud_degradada` con `dependencia: cola` y el tipo de error, nunca el
    mensaje de redis-py (L-007), exactamente una vez aunque el hilo termine
    después de vencido el plazo (D20)."""

    def _verificar() -> bool:
        resultado: queue.Queue[bool] = queue.Queue(maxsize=1)
        lock = threading.Lock()
        informado = [False]

        def _trabajo() -> None:
            try:
                cliente.ping()
                resultado.put(True)
            except Exception as error:
                # Mismo orden que el verificador de base: informar antes de
                # poner el resultado (gemelo, L-009).
                _informar_una_sola_vez(lock, informado, "cola", datos_de_excepcion(error))
                resultado.put(False)

        hilo = threading.Thread(target=_trabajo, daemon=True, context=contextvars.copy_context())
        hilo.start()
        try:
            return resultado.get(timeout=PLAZO_TOTAL_SALUD_S)
        except queue.Empty:
            # El hilo sigue colgado (Redis lento o congelado más allá del
            # plazo total): no esperamos más.
            _informar_una_sola_vez(lock, informado, "cola", None)
            return False

    return _verificar


def obtener_verificador_de_cola(request: Request) -> Callable[[], bool]:
    """Dependencia de FastAPI, inyectable: a diferencia del engine de base de
    datos (D18), el cliente síncrono de Redis no mantiene un pool caro de
    reutilizar, así que se crea uno nuevo por pedido a partir de la
    configuración (sin necesitar que `crear_app()` lo cablee en `app.state`)."""
    return _verificador_con_cliente_redis(cliente_redis_sincrono(Configuracion()))


def _ejecutar_verificaciones_en_paralelo(
    verificador_base: Callable[[], bool],
    verificador_cola: Callable[[], bool],
) -> tuple[bool, bool]:
    """Corre las dos verificaciones en paralelo, cada una en su propio hilo,
    y las espera contra un plazo total ÚNICO (D20, F13): el plazo se cuenta
    desde acá, una sola vez para las dos, así el tiempo de la respuesta es el
    de un plazo y no la suma de los dos, aunque las dos dependencias estén
    congeladas. No loguea nada por su cuenta: cada verificador (real o un
    verificador de prueba) es dueño de informar su propia falla."""
    plazo_limite = time.monotonic() + PLAZO_TOTAL_SALUD_S
    resultado_base: queue.Queue[bool] = queue.Queue(maxsize=1)
    resultado_cola: queue.Queue[bool] = queue.Queue(maxsize=1)

    def _correr(verificador: Callable[[], bool], resultado: queue.Queue[bool]) -> None:
        try:
            resultado.put(bool(verificador()))
        except Exception:
            resultado.put(False)

    # `context=contextvars.copy_context()` (B1, L-015): este hilo de afuera es
    # el que informa cuando VENCE el plazo contra una dependencia congelada
    # (el camino que `_informar_una_sola_vez` corre en `queue.Empty`, dentro
    # del propio verificador real, pero llamado desde acá): sin copiar el
    # contexto, esa línea pierde el `request_id` del pedido aunque el
    # verificador interno también copie el suyo. Una copia POR HILO: un mismo
    # objeto `Context` no se puede correr en dos hilos a la vez
    # (`RuntimeError: cannot enter context: ... is already entered`), aunque
    # los dos arranquen con los mismos valores.
    threading.Thread(
        target=_correr,
        args=(verificador_base, resultado_base),
        daemon=True,
        context=contextvars.copy_context(),
    ).start()
    threading.Thread(
        target=_correr,
        args=(verificador_cola, resultado_cola),
        daemon=True,
        context=contextvars.copy_context(),
    ).start()

    def _esperar(resultado: queue.Queue[bool]) -> bool:
        restante = plazo_limite - time.monotonic()
        try:
            return resultado.get(timeout=max(0.0, restante))
        except queue.Empty:
            return False

    return _esperar(resultado_base), _esperar(resultado_cola)


@router.get("/salud")
def salud(
    response: Response,
    verificador_base: Callable[[], bool] = Depends(obtener_verificador_de_base),
    verificador_cola: Callable[[], bool] = Depends(obtener_verificador_de_cola),
) -> dict[str, str]:
    base_responde, cola_responde = _ejecutar_verificaciones_en_paralelo(
        verificador_base, verificador_cola
    )

    cuerpo = {
        "estado": "ok" if base_responde and cola_responde else "degradado",
        "base": "ok" if base_responde else "sin_conexion",
        "cola": "ok" if cola_responde else "sin_conexion",
    }
    if not (base_responde and cola_responde):
        response.status_code = 503
    return cuerpo
