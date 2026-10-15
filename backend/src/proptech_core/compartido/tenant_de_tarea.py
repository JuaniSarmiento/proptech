"""El tenant del worker, por tarea (D4, D8, cambio 2a, tarea 7.1).

Cada tarea que toca datos de una administración recibe `administracion_id`
como argumento de ARQ (D2 de la cola: siempre texto, nunca un `UUID`
nativo — los trabajos viajan como JSON). `con_administracion_de_tarea` lo
valida ANTES de tocar nada:

1. Forma canónica ASCII (mismo patrón que `validar_request_id`, L-008): sólo
   dígitos hexadecimales ASCII, nunca un homoglifo Unicode que `int()`/`UUID()`
   podrían aceptar en silencio como si fuera un dígito.
2. Un modelo Pydantic estricto (`UUID`, `strict=True`, D8) sobre el valor ya
   parseado, como exige el diseño.

Si no es válido — falta, vacío, en blanco, un entero, un texto que no es un
UUID, o un UUID con dígitos no ASCII — la tarea falla UNA sola vez: la
excepción (`AdministracionInvalida`) nunca es de las que `reintentable`
reintenta, y este decorador va POR FUERA de `reintentable` en la pila (D3),
así que ni siquiera llega a invocar la función reintentable — cero
reintentos, no "reintentable decide no reintentar". El evento fijo
`tarea_sin_administracion` nunca lleva el valor recibido (L-007).

Si valida, le pasa a la tarea el `UUID` ya parseado (nunca el texto crudo) y,
si la tarea también recibe `clave` (D3, idempotencia), le agrega el
`administracion_id` adelante: `trabajos_hechos` tiene una sola clave global
(E3), y sin esto dos administraciones con la misma clave lógica se pisarían.

No hay estado ambiente que pase de una tarea a la siguiente (D8): cada
llamada valida y arma sus propios argumentos desde cero, nunca una
`ContextVar` ni un valor en `ctx` que sobreviva entre tareas.
"""

from __future__ import annotations

import functools
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

_logger = logging.getLogger("proptech_core.compartido.tenant_de_tarea")

_PATRON_UUID_CANONICO = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    flags=re.ASCII,
)


class AdministracionInvalida(Exception):
    """`administracion_id` no es un UUID canónico válido (D8): el mensaje
    nunca lleva el valor recibido."""


class _AdministracionId(BaseModel):
    model_config = ConfigDict(strict=True)

    administracion_id: UUID


def _administracion_validada(valor: Any) -> UUID:
    if not isinstance(valor, str) or not _PATRON_UUID_CANONICO.fullmatch(valor):
        raise AdministracionInvalida("administracion_id inválido (D8)")
    try:
        candidato = UUID(valor)
    except ValueError:
        raise AdministracionInvalida("administracion_id inválido (D8)") from None
    try:
        return _AdministracionId(administracion_id=candidato).administracion_id
    except ValidationError:
        raise AdministracionInvalida("administracion_id inválido (D8)") from None


def con_administracion_de_tarea[R](
    func: Callable[..., Awaitable[R]],
) -> Callable[..., Awaitable[R]]:
    @functools.wraps(func)
    async def envoltorio(
        ctx: dict[str, Any], *args: Any, administracion_id: Any = None, **kwargs: Any
    ) -> R:
        try:
            validado = _administracion_validada(administracion_id)
        except AdministracionInvalida:
            tarea_nombre = ctx.get("job_name", func.__name__)
            _logger.error("tarea_sin_administracion", extra={"tarea": tarea_nombre})
            raise

        clave = kwargs.get("clave")
        if isinstance(clave, str):
            kwargs["clave"] = f"{validado}:{clave}"

        return await func(ctx, *args, administracion_id=validado, **kwargs)

    return envoltorio
