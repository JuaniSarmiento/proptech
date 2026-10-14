"""Formato de logs: una línea JSON por evento con una lista cerrada de campos (D7).

`evento` es siempre la plantilla del mensaje (`record.msg`), nunca el resultado de
interpolar sus argumentos: así ningún dato pasado como argumento de
``logger.info("plantilla %s", dato)`` llega a la salida.
"""

import json
import logging
import re
import sys
import traceback
from datetime import UTC, datetime
from types import TracebackType

from proptech_core.compartido.seguimiento import FiltroRequestId

#: Cuadros máximos que guarda `datos_de_excepcion` en `traza` (D7).
CUADROS_MAXIMOS_TRAZA = 10

#: Loggers cuyos handlers reemplaza `configurar_logs` (D7): la raíz, los dos
#: de uvicorn (uvicorn ya configuró los suyos antes de importar la app) y el
#: de ARQ.
_LOGGERS_A_RECABLEAR = ("", "uvicorn", "uvicorn.error", "arq")

#: Campos extra permitidos, además de los campos base (ts, nivel, servicio,
#: logger, evento, request_id). Lista blanca: un campo fuera de esta lista se
#: descarta y se cuenta en `campos_descartados` (D7).
CAMPOS_PERMITIDOS = frozenset(
    {
        "metodo",
        "ruta",
        "estado",
        "duracion_ms",
        "tarea",
        "clave",
        "intento",
        "intentos_maximos",
        "espera_s",
        "resultado",
        "tipo_error",
        "traza",
        "dependencia",
        "componente",
    }
)

# Atributos propios de un LogRecord recién creado (sin nada de `extra`), para
# distinguirlos de los campos que sí pasó quien llamó al logger. Se calcula
# contra un record de plantilla en vez de hardcodear la lista para no
# depender de qué atributos agrega cada versión de Python (por ejemplo
# `taskName`, agregado en 3.12).
_RECORD_PLANTILLA = logging.LogRecord("plantilla", logging.INFO, "", 0, "", (), None)
_ATRIBUTOS_ESTANDAR = frozenset(_RECORD_PLANTILLA.__dict__.keys())


def _timestamp_utc_ms(epoch_segundos: float) -> str:
    """`ts` en UTC, ISO 8601 con milisegundos y sufijo `Z` (D7)."""
    momento = datetime.fromtimestamp(epoch_segundos, tz=UTC)
    milisegundos = momento.microsecond // 1000
    return momento.strftime("%Y-%m-%dT%H:%M:%S") + f".{milisegundos:03d}Z"


class FormateadorJSON(logging.Formatter):
    """Una línea JSON por evento, sin dependencias externas.

    Los campos base van en este orden: `ts`, `nivel`, `servicio`, `logger`,
    `evento` y, cuando exista, `request_id`. Después, los campos extra de la
    lista blanca, en el orden en que se pasaron. `campos_descartados` cuenta
    los campos fuera de la lista y sólo aparece si hubo alguno.
    """

    def __init__(self, servicio: str) -> None:
        super().__init__()
        self._servicio = servicio

    def format(self, record: logging.LogRecord) -> str:
        datos: dict[str, object] = {
            "ts": _timestamp_utc_ms(record.created),
            "nivel": record.levelname.lower(),
            "servicio": self._servicio,
            "logger": record.name,
        }
        if isinstance(record.msg, BaseException):
            # D13, L-007, vuelta 3 (F7b): `uvicorn/server.py` y `config.py`
            # hacen `logger.error(exc)`: la excepción entera como `msg`. Su
            # `str()` ES el mensaje de la excepción (puede traer datos del
            # usuario o de la conexión); `evento` nunca puede ser eso, nunca
            # es una plantilla acá porque no la hay. Evento fijo, y
            # `tipo_error`/`traza` salen de la excepción, nunca de su texto.
            datos["evento"] = EVENTO_EXCEPCION_COMO_MENSAJE
            datos.update(datos_de_excepcion(record.msg))
        else:
            mensaje = str(record.msg)
            datos["evento"] = mensaje
            if _es_traceback_crudo(mensaje):
                # `evento` como plantilla no alcanza acá (D7): todo el
                # mensaje YA es el texto de la excepción fundido por quien lo
                # generó (nunca lo armamos nosotros), así que se descarta
                # entero y se reconstruye `tipo_error`/`traza` parseando el
                # traceback, nunca repitiendo su texto (L-007).
                datos["evento"] = EVENTO_TRACEBACK_CRUDO_DESCARTADO
                datos["tipo_error"] = _tipo_de_traceback_crudo(mensaje)
                datos["traza"] = _traza_de_traceback_crudo(mensaje)

        request_id = record.__dict__.get("request_id")
        if request_id:
            datos["request_id"] = request_id

        campos_descartados = 0
        for clave, valor in record.__dict__.items():
            if clave in _ATRIBUTOS_ESTANDAR or clave == "request_id":
                continue
            if clave not in CAMPOS_PERMITIDOS:
                campos_descartados += 1
                continue
            datos[clave] = valor

        if campos_descartados:
            datos["campos_descartados"] = campos_descartados

        return json.dumps(datos, ensure_ascii=False)


#: Marca el inicio de un traceback de Python ya formateado como texto
#: (D7, L-007): Starlette arma así el mensaje de `lifespan.startup.failed`
#: (`traceback.format_exc()`) y uvicorn lo loguea en `uvicorn.error` con
#: `logger.error(message["message"])`, sin `exc_info`: para cuando llega al
#: formatter, el mensaje de la excepción y las líneas de código ya están
#: fundidos en el string de `record.msg`, no hay objeto de excepción que
#: `datos_de_excepcion` pueda inspeccionar.
_MARCA_TRACEBACK_CRUDO = "Traceback (most recent call last):"

#: Un cuadro de un traceback ya formateado: `  File "archivo", line N, in func`.
_PATRON_CUADRO_TRACEBACK_CRUDO = re.compile(
    r'File "(?P<archivo>[^"]+)", line (?P<linea>\d+), in (?P<funcion>\S+)'
)

#: Evento fijo para un traceback crudo descartado (D7, L-007): nunca el texto
#: original, que puede traer el mensaje de la excepción (con datos del
#: usuario o de la conexión) y las líneas de código.
EVENTO_TRACEBACK_CRUDO_DESCARTADO = "traceback_crudo_descartado"

#: Evento fijo cuando `record.msg` es la excepción misma, no una plantilla
#: (D13, L-007, vuelta 3 F7b): no hay texto propio que mostrar como `evento`.
EVENTO_EXCEPCION_COMO_MENSAJE = "excepcion_como_mensaje"

#: Un nombre de excepción válido: identificador ASCII que termina en uno de
#: estos sufijos, sin espacios (vuelta 3, F7b). Sirve para reconocer la línea
#: `TipoError: ...` de un traceback crudo sin confundirla con una línea de
#: continuación del MENSAJE (que puede tener dos puntos y seguir sin tener la
#: forma de un nombre de clase: con espacios, con guiones, etc).
_PATRON_NOMBRE_DE_EXCEPCION = re.compile(
    r"[A-Za-z_][\w.]*(?:Error|Exception|Warning|Exit|Interrupt)", re.ASCII
)


def _es_traceback_crudo(mensaje: str) -> bool:
    return _MARCA_TRACEBACK_CRUDO in mensaje


def _tipo_de_traceback_crudo(mensaje: str) -> str:
    """El nombre de la excepción, buscado de atrás para adelante entre las
    líneas no vacías (D7, L-007, vuelta 3 F7b).

    La vuelta 2 tomaba la ÚLTIMA línea entera como candidato: con un mensaje
    de varias líneas (`psycopg`/SQLAlchemy lo hacen: "Is the server
    running..."), esa última línea es parte del MENSAJE, no el tipo, y
    terminaba en `tipo_error`. Acá cada línea se recorta antes de los
    primeros dos puntos y sólo se acepta como tipo si ese recorte
    `fullmatch`ea un nombre de excepción (`_PATRON_NOMBRE_DE_EXCEPCION`):
    una línea de continuación del mensaje (con espacios, con guiones, sin la
    forma de un identificador) nunca lo hace, aunque tenga dos puntos."""
    for linea in reversed(mensaje.splitlines()):
        candidato = linea.split(":", 1)[0].strip()
        if candidato and _PATRON_NOMBRE_DE_EXCEPCION.fullmatch(candidato):
            return candidato
    return "ErrorDesconocido"


def _traza_de_traceback_crudo(mensaje: str) -> list[str]:
    cuadros = [
        f"{coincidencia['archivo']}:{coincidencia['linea']}:{coincidencia['funcion']}"
        for coincidencia in _PATRON_CUADRO_TRACEBACK_CRUDO.finditer(mensaje)
    ]
    return cuadros[:CUADROS_MAXIMOS_TRAZA]


def _nombre_calificado(tipo: type) -> str:
    return f"{tipo.__module__}.{tipo.__qualname__}"


def _traza_sin_mensaje_ni_codigo(tb: TracebackType | None) -> list[str]:
    """Hasta `CUADROS_MAXIMOS_TRAZA` cuadros `modulo:línea:función`, sin el
    mensaje de la excepción ni el texto de la línea de código fuente (D7,
    L-007): sólo lo que trae cada `FrameSummary` en `filename`, `lineno` y
    `name`, nunca `line`."""
    cuadros = traceback.extract_tb(tb)
    return [f"{cuadro.filename}:{cuadro.lineno}:{cuadro.name}" for cuadro in cuadros][
        :CUADROS_MAXIMOS_TRAZA
    ]


def datos_de_excepcion(excepcion: BaseException) -> dict[str, object]:
    """`tipo_error` y `traza` de una excepción, nunca su mensaje (D7, D13).

    Pensado para pasarse como `extra` a un logger: ninguno de los dos valores
    repite el texto de `str(excepcion)`, así el mensaje de una biblioteca de
    terceros (psycopg, redis-py, ARQ) nunca llega a la salida.
    """
    return {
        "tipo_error": _nombre_calificado(type(excepcion)),
        "traza": _traza_sin_mensaje_ni_codigo(excepcion.__traceback__),
    }


def configurar_logs(servicio: str) -> None:
    """Reemplaza los handlers de la raíz, `uvicorn`, `uvicorn.error` y `arq`
    por uno solo a `stdout` con `FormateadorJSON` (D7).

    Llamarla más de una vez (por ejemplo si el proceso reconfigura sus logs)
    no duplica líneas: cada llamada vacía la lista de handlers del logger
    antes de agregar el suyo, en vez de sumarse a los que ya había.
    """
    formateador = FormateadorJSON(servicio=servicio)
    for nombre in _LOGGERS_A_RECABLEAR:
        logger = logging.getLogger(nombre)
        for handler_viejo in list(logger.handlers):
            logger.removeHandler(handler_viejo)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formateador)
        handler.addFilter(FiltroRequestId())
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.INFO)
