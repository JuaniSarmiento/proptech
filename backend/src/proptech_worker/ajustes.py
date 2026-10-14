"""Settings de ARQ para el worker (`AjustesDelWorker`, D2, D3, D8). Cambio
1c, tarea 5.5.

Falla rápido al arrancar (igual que `proptech_api.app.crear_app`, D11): si
falta o es inválida una variable de configuración, o el archivo de
parámetros, el proceso termina acá nombrando el problema, antes de que ARQ
intente conectarse a Redis (tarea 5.9).
"""

from __future__ import annotations

import logging
import sys
from types import TracebackType
from typing import Any

from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_application_name,
)
from proptech_core.compartido.cola import deserializar_job, serializar_job
from proptech_core.compartido.conexion_redis import ajustes_redis_arq
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.logs import FormateadorJSON, configurar_logs
from proptech_core.compartido.parametros import leer_parametros
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import tarea_de_prueba

#: Config de `logging.config.dictConfig` para el CLI de ARQ (D7, D13, L-007,
#: vuelta 3 F12): `arq/cli.py` hace SIEMPRE `dictConfig(...)` justo después
#: de importar este módulo (que ya corrió `configurar_logs` arriba) y ANTES
#: de que `Worker.main()` cree el pool de Redis (`arq/worker.py`, antes de
#: `on_startup`, que es donde el resto de este archivo reconfiguraría los
#: logs si el CLI los pisó). Con la config por default de ARQ
#: (`arq.logs.default_log_config`) ese `dictConfig` reemplaza el handler del
#: logger "arq" por uno de texto plano que interpola los argumentos: si
#: Redis es inalcanzable, `create_pool` logea ahí el error de conexión de
#: redis-py (host, puerto, mensaje) varias veces antes de agotar los
#: reintentos, sin pasar nunca por `FormateadorJSON`.
#:
#: `arq/cli.py` sólo cambia esa config por otra si se le pasa
#: `--custom-log-dict`, pero D2 y la tarea 5.10 fijan el `command` del
#: servicio `worker` de Compose como `["arq",
#: "proptech_worker.ajustes.AjustesDelWorker"]`, sin esa opción (y
#: `test_worker_usa_la_imagen_de_api_con_comando_arq` lo exige literal). En
#: vez de tocar el comando, se pisa `arq.cli.default_log_config` (la función
#: que `cli()` llama cuando no hay `--custom-log-dict`, importada por
#: nombre en el módulo de ARQ) para que devuelva ESTA config. El `import` de
#: `proptech_worker.ajustes` corre siempre antes de ese `dictConfig` (el CLI
#: primero importa `worker_settings`, después configura logging), así que el
#: pisado ya está en su lugar a tiempo.
CONFIG_DE_LOGS_DEL_CLI: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "proptech_core.compartido.seguimiento.FiltroRequestId"},
    },
    "formatters": {
        "json": {"()": "proptech_core.compartido.logs.FormateadorJSON", "servicio": "worker"},
    },
    "handlers": {
        "arq.json": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "arq": {"handlers": ["arq.json"], "level": "INFO", "propagate": False},
    },
}


#: Los cuatro paquetes que D13 nombra como fuente de mensajes ajenos que
#: nunca se repiten (redis-py, ARQ, psycopg, SQLAlchemy). `ConfiguracionInvalida`,
#: `ArgumentoDeTareaInvalido` y la `ValidationError` de `leer_parametros` son
#: EXCEPCIONES PROPIAS que ya nombran la variable o el campo sin su valor
#: (D11, L-002): ésas tienen que seguir llegando a `stderr` como siempre (la
#: tarea 5.9 lo exige), nunca pasar por acá.
_PREFIJOS_DE_TERCEROS = ("redis", "arq", "psycopg", "sqlalchemy")


def _es_excepcion_de_terceros(tipo: type[BaseException]) -> bool:
    modulo = tipo.__module__ or ""
    return any(
        modulo == prefijo or modulo.startswith(f"{prefijo}.") for prefijo in _PREFIJOS_DE_TERCEROS
    )


def _registrar_excepcion_no_atrapada(
    tipo: type[BaseException], valor: BaseException, traza: TracebackType | None
) -> None:
    """Reemplaza el traceback crudo que el `excepthook` default de Python
    imprime directo a `stderr` ante una excepción sin atrapar DE TERCEROS
    (D13, L-007, vuelta 3 F12): el CLI de ARQ no atrapa el error de
    `create_pool` cuando los reintentos de conexión a Redis se agotan, y ese
    traceback lleva el mensaje de redis-py (host y puerto incluidos), sin
    pasar por ningún logger. Acá se loguea como cualquier otra excepción (D7,
    D13): sólo `tipo_error` y `traza` (vía el formatter, pasando la excepción
    misma como `msg`), nunca su mensaje.

    `KeyboardInterrupt` y cualquier excepción que NO sea de uno de los cuatro
    paquetes de D13 (en particular las propias, D11) siguen el camino normal:
    ese traceback es información nuestra, pensada para llegar a `stderr`."""
    if issubclass(tipo, KeyboardInterrupt) or not _es_excepcion_de_terceros(tipo):
        sys.__excepthook__(tipo, valor, traza)
        return
    logging.getLogger("arq").error(valor)


sys.excepthook = _registrar_excepcion_no_atrapada


def _dictconfig_json_del_cli(verbose: bool) -> dict[str, Any]:
    """Reemplazo de `arq.logs.default_log_config` (vuelta 3 F12): mismo tipo
    de retorno, pero con `FormateadorJSON` en vez del texto plano de ARQ."""
    return CONFIG_DE_LOGS_DEL_CLI


try:
    import arq.cli as _arq_cli

    _arq_cli.default_log_config = _dictconfig_json_del_cli  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - `arq.cli` necesita `click` (D1, ya es dependencia)
    pass

# Antes que nada: logs en JSON (D7). Falla rápido si la configuración o los
# parámetros son inválidos (D11), nombrando el problema, antes de construir
# `redis_settings` (que ya necesita leer la contraseña de Redis).
configurar_logs("worker")
_configuracion = Configuracion()
leer_parametros(_configuracion.proptech_parametros)

#: Espera base e intentos máximos de producción (D3): 2, 4, 8, 16 s.
POLITICA_DE_PRODUCCION = PoliticaReintentos()


def _logs_json_del_worker_activos() -> bool:
    """`True` si el logger `arq` todavía tiene el handler que pone
    `configurar_logs` (D7): un `StreamHandler` con `FormateadorJSON`.

    No exige que sea el ÚNICO handler (sólo que exista): pytest, cuando un
    logger tiene `propagate=False` (como deja `configurar_logs`), le agrega
    su propio `LogCaptureHandler` AL LADO del nuestro para poder capturarlo
    igual (`_pytest/logging.py`), así que en los tests `arq` termina con más
    de un handler sin que el propio (el JSON) se haya ido."""
    return any(
        isinstance(handler.formatter, FormateadorJSON)
        for handler in logging.getLogger("arq").handlers
    )


async def on_startup(ctx: dict[str, Any]) -> None:
    """Abre un único engine por proceso (D2): mismos parámetros de pool que
    el de la API, tomados de la configuración (D18, L-009), y
    `application_name=proptech-worker` como nombre base de la conexión
    (D8: el evento `after_begin` lo sobreescribe por transacción con el
    `request_id` en curso).

    Logs en JSON otra vez si hace falta (D7): el CLI de ARQ (`arq
    proptech_worker.ajustes...`, el que usa Compose y su healthcheck)
    importa este módulo, que ya llamó `configurar_logs` arriba, pero
    DESPUÉS de importarlo el CLI hace
    `logging.config.dictConfig(default_log_config(...))`, que pisa el
    handler del logger `arq` por el suyo (texto plano, con los argumentos
    del trabajo interpolados). `on_startup` corre después de eso: si el
    handler de `arq` ya no es el propio, se reconfigura antes de que el
    worker tome ningún trabajo. **Sólo si hace falta**: los tests que
    corren `on_startup` en proceso (sin pasar por el CLI) redirigen el
    `.stream` del handler ya puesto por la llamada de arriba para capturar
    los logs; reconfigurar siempre, incondicionalmente, los dejaría
    escribiendo a un handler nuevo y rompería esa captura (`configurar_logs`
    reemplaza los handlers en cada llamada, nunca reutiliza el objeto)."""
    if not _logs_json_del_worker_activos():
        configurar_logs("worker")
    engine = crear_engine(_configuracion, connect_args={"application_name": "proptech-worker"})
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_application_name(fabrica, "proptech-worker")
    ctx["engine"] = engine
    ctx["fabrica_de_sesiones"] = fabrica
    ctx["politica"] = POLITICA_DE_PRODUCCION


async def on_shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        engine.dispose()


class AjustesDelWorker:
    """`arq proptech_worker.ajustes.AjustesDelWorker` (D2). ARQ lee estos
    atributos de clase (`arq.worker.get_kwargs`) para construir el
    `arq.Worker`."""

    functions = (tarea_de_prueba,)
    #: El worker reintenta más que la API al conectar a Redis (D4): un
    #: reinicio de Redis no tiene por qué tirar abajo los trabajos ya
    #: tomados.
    redis_settings = ajustes_redis_arq(_configuracion, conn_retries=5)
    on_startup = staticmethod(on_startup)
    on_shutdown = staticmethod(on_shutdown)
    #: Serialización JSON (D2): el default de ARQ es `pickle`. El mismo
    #: serializador que usa el pool que encola (`cola.py`, L-009).
    job_serializer = staticmethod(serializar_job)
    job_deserializer = staticmethod(deserializar_job)
    max_tries = 5
    job_timeout = 120
    keep_result = 3600
    #: ARQ no escribe el resultado de cada trabajo (D7, M25): ya se
    #: descartan los argumentos (el formatter ignora `record.args`), pero
    #: esto evita depender de un solo candado (tarea 5.7).
    log_results = False
    #: El default de ARQ es una hora; el healthcheck de Compose (tarea
    #: 5.10) necesita que el chequeo falle a tiempo.
    health_check_interval = 30
