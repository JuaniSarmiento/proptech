"""El número de seguimiento (`request_id`): validación y propagación (D8).

Un valor válido es un UUID en forma canónica (36 caracteres, `8-4-4-4-12`
hexadecimal), con sólo dígitos y letras ASCII. Se valida con coincidencia
completa sobre el texto entero, con la bandera `re.ASCII`, **antes** de
normalizar a minúsculas (L-008): nunca se recorta ni se pasa a minúsculas un
valor para después aceptarlo, porque `strip()` se comería un salto de línea
final y `lower()` de Unicode podría convertir un carácter ajeno.
"""

import functools
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

#: El `request_id` del pedido en curso (D8). Lo fija el middleware de la API
#: y el decorador de la tarea del worker; lo lee el formatter de logs (a
#: través de `FiltroRequestId`) y el evento `after_begin` de la sesión de
#: PostgreSQL. `None` fuera de un pedido o una tarea.
request_id_actual: ContextVar[str | None] = ContextVar("request_id_actual", default=None)


class FiltroRequestId(logging.Filter):
    """Agrega `request_id` a todo log registrado dentro de un pedido o una
    tarea, sin que quien llame al logger tenga que pasarlo a mano en cada
    `extra` (D8). No pisa un `request_id` que el propio llamador ya puso."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            valor = request_id_actual.get()
            if valor is not None:
                record.request_id = valor
        return True


_PATRON_UUID_CANONICO = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    flags=re.ASCII,
)


def validar_request_id(valor: str) -> str | None:
    """Devuelve el valor normalizado a minúsculas si es un UUID canónico
    válido, o `None` si no lo es (quien llama genera uno nuevo en ese caso)."""
    if not _PATRON_UUID_CANONICO.fullmatch(valor):
        return None
    return valor.lower()


_logger_seguimiento = logging.getLogger("proptech_core.compartido.seguimiento")


def con_seguimiento_de_tarea[R](
    func: Callable[..., Awaitable[R]],
) -> Callable[..., Awaitable[R]]:
    """Decora una tarea del worker (D8): fija `request_id_actual` con el
    argumento `request_id` antes de correr la tarea (así los logs y el
    `application_name` de la sesión lo toman de ahí) y la limpia al
    terminar, incluso si la tarea lanza.

    Si `request_id` falta o no es un UUID canónico válido, se genera uno
    nuevo y se loguea `request_id_reemplazado`: la tarea siempre corre con
    un `request_id` válido."""

    @functools.wraps(func)
    async def envoltorio(
        ctx: dict[str, Any], *args: Any, request_id: str | None = None, **kwargs: Any
    ) -> R:
        # Default `None` (no obligatorio): un trabajo armado a mano, o
        # encolado por código que se olvidó el argumento, llega SIN
        # `request_id`. Exigirlo como argumento obligatorio sin default
        # hacía que Python levantara `TypeError` antes de que este cuerpo
        # pudiera reemplazarlo, igual que con un valor inválido (D8).
        validado = validar_request_id(request_id) if isinstance(request_id, str) else None
        if validado is None:
            validado = str(uuid.uuid4())
            _logger_seguimiento.warning("request_id_reemplazado")
        token = request_id_actual.set(validado)
        try:
            return await func(ctx, *args, request_id=validado, **kwargs)
        finally:
            request_id_actual.reset(token)

    return envoltorio
