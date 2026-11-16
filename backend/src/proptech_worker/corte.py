"""Corte del lado de la base para las tareas del worker (H-016, F2c, D-158).

`asyncio.wait_for` corta la espera del event loop, no el hilo que habla con la base: un hilo
colgado puede confirmar su efecto cuando la base vuelve, con el trabajo ya dado por agotado. Acá
la cota vive en la transacción: `statement_timeout`, `lock_timeout` e
`idle_in_transaction_session_timeout` la cortan en el servidor, y un chequeo del plazo antes de
confirmar cubre lo que la base no ve (un efecto que corre en Python). Todo corte revierte y
levanta `CorteDeLaBase`, un `ErrorPasajero`: se reintenta y, agotado, nunca deja un efecto
confirmado.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import sqlalchemy.exc
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.idempotencia import ejecutar_una_vez
from proptech_core.compartido.reintentos import ErrorPasajero

_PARAMETROS_DE_CORTE = (
    "statement_timeout",
    "lock_timeout",
    "idle_in_transaction_session_timeout",
)


class CorteDeLaBase(ErrorPasajero):
    """La tarea pasó su cota (sentencia, candado, inactividad o plazo) y no confirmó nada."""


def traducir_error_de_base(error: BaseException) -> CorteDeLaBase | None:
    """Un corte del servidor (cancelación por timeout, candado no disponible, conexión cerrada)
    llega como error operacional o de interfaz del driver; otro error de la base no es un corte."""
    if isinstance(error, sqlalchemy.exc.OperationalError | sqlalchemy.exc.InterfaceError):
        return CorteDeLaBase("la base cortó la operación")
    if isinstance(error, sqlalchemy.exc.DBAPIError) and error.connection_invalidated:
        return CorteDeLaBase("la conexión con la base se perdió")
    return None


def envolver_con_plazo(
    efecto: Callable[[Session], None],
    cota_s: float,
    *,
    reloj: Callable[[], float] = time.monotonic,
) -> Callable[[Session], None]:
    """Corre `efecto` y, si al terminar ya pasó `cota_s` desde que se armó el envoltorio, levanta
    `CorteDeLaBase` antes de que alguien confirme."""
    inicio = reloj()

    def con_plazo(sesion: Session) -> None:
        efecto(sesion)
        if reloj() - inicio > cota_s:
            raise CorteDeLaBase("el efecto terminó después del plazo de la tarea")

    return con_plazo


def _fijar_cotas(sesion: Session, cota_s: float) -> None:
    milisegundos = max(1, round(cota_s * 1000))
    for parametro in _PARAMETROS_DE_CORTE:
        sesion.execute(
            text("SELECT set_config(:parametro, :valor, true)"),
            {"parametro": parametro, "valor": str(milisegundos)},
        )


def ejecutar_con_corte(
    fabrica: sessionmaker[Session],
    *,
    administracion_id: uuid.UUID | None,
    cota_s: float,
    clave: str,
    tarea: str,
    request_id: str,
    efecto: Callable[[Session], None],
) -> bool:
    """`ejecutar_una_vez` con la cota de la tarea fijada con `SET LOCAL` y el plazo verificado
    antes de confirmar. Devuelve lo mismo que `ejecutar_una_vez`; ante un corte, revierte y
    levanta `CorteDeLaBase`."""
    envuelto = envolver_con_plazo(efecto, cota_s)
    with abrir_sesion(fabrica, administracion_id) as sesion:
        try:
            _fijar_cotas(sesion, cota_s)
            return ejecutar_una_vez(
                sesion, clave=clave, tarea=tarea, request_id=request_id, efecto=envuelto
            )
        except CorteDeLaBase:
            _revertir(sesion)
            raise
        except sqlalchemy.exc.DBAPIError as error:
            corte = traducir_error_de_base(error)
            _revertir(sesion)
            if corte is None:
                raise
            raise corte from error


def _revertir(sesion: Session) -> None:
    try:
        sesion.rollback()
    except sqlalchemy.exc.DBAPIError:
        pass  # la conexión ya murió en el servidor: no hay nada que revertir
