"""Política de reintentos de las tareas del worker (D3): sólo un error
pasajero se reintenta, con una espera que se duplica en cada intento, hasta
un máximo. Cambio 1c, tarea 5.3.

`política` (espera base e intentos máximos) se arma en `on_startup` del
worker y viaja en `ctx["politica"]` (D3, tarea 5.5): el decorador la lee en
cada llamada, nunca la fija al decorar.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import redis.exceptions
import sqlalchemy.exc
from arq import Retry

from proptech_core.compartido.logs import datos_de_excepcion

_logger = logging.getLogger("proptech_core.compartido.reintentos")


class ErrorPasajero(Exception):
    """Marca una falla pasajera (dependencia caída, que no responde o
    lenta) que vale la pena reintentar (D3)."""


#: Errores pasajeros "por naturaleza" (D3), además de `ErrorPasajero` (el
#: propio): errores de conexión y timeout de SQLAlchemy, de redis-py y los
#: genéricos de la biblioteca estándar. `sqlalchemy.exc.TimeoutError` es el
#: pool de conexiones agotado (vuelta 3, F2b): también pasajero, no sólo la
#: base caída o congelada.
_ERRORES_PASAJEROS_POR_NATURALEZA: tuple[type[BaseException], ...] = (
    sqlalchemy.exc.OperationalError,
    sqlalchemy.exc.TimeoutError,
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
    TimeoutError,
    ConnectionError,
)


def _es_pasajero(error: BaseException) -> bool:
    return isinstance(error, ErrorPasajero) or isinstance(error, _ERRORES_PASAJEROS_POR_NATURALEZA)


@dataclass(frozen=True)
class PoliticaReintentos:
    """Espera base (segundos) e intentos máximos (D3).

    Con `espera_base=2.0` (el valor de producción) las esperas son 2, 4, 8,
    16: `espera_base * 2 ** (intento - 1)`. Sin jitter: con un solo worker no
    hay estampida y la espera determinista se puede afirmar en un test. Los
    tests usan una espera base de 0,05 s (tarea 5.5).
    """

    espera_base: float = 2.0
    intentos_maximos: int = 5


def _espera(politica: PoliticaReintentos, intento: int) -> float:
    return float(politica.espera_base * 2 ** (intento - 1))


def reintentable[R](
    func: Callable[..., Awaitable[R]],
) -> Callable[..., Awaitable[R]]:
    """Decora una tarea de ARQ (`async def tarea(ctx, ...)`).

    Reintenta sólo un error pasajero (`ErrorPasajero` o uno de los que lo
    son por naturaleza), con la espera de `ctx["politica"]` y el número de
    intento de `ctx["job_try"]` (D3):

    - Si no es el último intento: loguea `reintento_programado` y levanta
      `arq.Retry(defer=espera)`.
    - Si es el último intento: loguea `tarea_agotada` con nivel `error` y
      relanza la excepción original (ARQ la marca fallida).
    - Cualquier otro error (no pasajero): loguea `tarea_fallida` con nivel
      `error` y relanza, sin reintento.

    Ninguno de los tres eventos repite el mensaje de la excepción (L-007):
    sólo viaja `tipo_error` (y, en los dos primeros, `intento`/`espera_s`),
    nunca `str(error)`.
    """

    @functools.wraps(func)
    async def envoltorio(ctx: dict[str, Any], *args: Any, **kwargs: Any) -> R:
        try:
            return await func(ctx, *args, **kwargs)
        except Exception as error:
            tarea_nombre = ctx.get("job_name", func.__name__)
            if not _es_pasajero(error):
                _logger.error(
                    "tarea_fallida",
                    extra={"tarea": tarea_nombre, **datos_de_excepcion(error)},
                )
                raise

            politica: PoliticaReintentos = ctx["politica"]
            intento: int = ctx["job_try"]
            if intento >= politica.intentos_maximos:
                _logger.error(
                    "tarea_agotada",
                    extra={
                        "tarea": tarea_nombre,
                        "intento": intento,
                        "intentos_maximos": politica.intentos_maximos,
                        **datos_de_excepcion(error),
                    },
                )
                raise

            espera = _espera(politica, intento)
            _logger.warning(
                "reintento_programado",
                extra={
                    "tarea": tarea_nombre,
                    "intento": intento,
                    "intentos_maximos": politica.intentos_maximos,
                    "espera_s": espera,
                    **datos_de_excepcion(error),
                },
            )
            raise Retry(defer=espera) from error

    return envoltorio
