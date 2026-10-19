"""Ids que siempre genera el servidor (R11, D7 del design, E8).

El cuerpo de toda alta (`POST`) hereda de `CuerpoDeAlta`, que rechaza
cualquier campo no declarado explícitamente (`extra="forbid"`) y no
coacciona tipos por sorpresa (`strict=True`, D-046: nada de `bool` donde se
espera `str`, ni `"123"` donde se espera un número). Un cliente que manda
`id`, `administracion_id` o `complejo_id` sin que la ruta los declare da
422 en vez de que el valor se ignore en silencio.

`strict=True` a nivel del modelo entero chocaría con cómo FastAPI valida el
cuerpo: lo hace con el dict ya parseado de JSON (modo "python" de pydantic,
no modo "json"), y en modo "python" estricto un `UUID` exige una instancia
de `UUID`, no el texto que es la única forma en que JSON puede representarlo
— rompería cualquier alta real. Por eso cada campo `UUID` de un cuerpo que
hereda de `CuerpoDeAlta` necesita `Annotated[UUID, Field(strict=False)]`
(ver `proptech_api.complejos.CuerpoAsignacion`): el resto de los campos sigue
estricto, sólo el `UUID` vuelve a aceptar su representación de texto.

El 422 de FastAPI por defecto repite el valor rechazado en `input` (y a
veces en `ctx`) — L-007, el error de una librería es una fuga. El cuerpo
`id` del alta nunca se declara en ningún modelo de dominio, así que
siempre cae como "extra_forbidden"; `manejador_422` reemplaza la respuesta
por una que nombra sólo el campo (`loc`) y el motivo (`type`/`msg`), para
TODA ruta de la app, nunca el valor.
"""

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic_core import ErrorDetails

#: R3A-5 (L-007): el único `type` cuyo `msg` es nuestro, no de pydantic — lo
#: arma pydantic como "Value error, <mensaje>" a partir de un `ValueError`
#: que nosotros escribimos a mano en cada `field_validator`/`AfterValidator`
#: del cambio (p.ej. `texto.py`, `_nombre_valido`), y esos mensajes ya están
#: auditados para nunca repetir el valor del cliente (L-007, L-002). Para
#: cualquier otro `type` (uuid_parsing, int_parsing, literal_error, ...),
#: `msg` lo genera pydantic y puede incluir el fragmento rechazado (un
#: carácter, una longitud) — blanquear por tipo conocido es frágil, así que
#: se blanquea todo lo que no está en esta lista.
_TIPOS_CON_MENSAJE_PROPIO = frozenset({"value_error"})


def _motivo(error: ErrorDetails) -> str:
    if error["type"] in _TIPOS_CON_MENSAJE_PROPIO:
        return error["msg"]
    return f"valor inválido ({error['type']})"


class CuerpoDeAlta(BaseModel):
    """Modelo base de todo cuerpo de alta (`POST`) bajo `/api` (R11)."""

    model_config = ConfigDict(extra="forbid", strict=True)


async def manejador_422(_request: Request, exc: Exception) -> JSONResponse:
    """Mismo código 422 de siempre, con el detalle saneado: cada error
    conserva `type` y `loc` (describen el CAMPO), y un `msg` que describe el
    motivo SIN ningún fragmento del valor (`_motivo`, L-007) — nunca `input`
    ni `ctx`, que pydantic sí llena con el valor que mandó el cliente.

    La firma recibe `Exception`, no `RequestValidationError`, porque así la
    tipa `Starlette.add_exception_handler` (el registro es por clase, pero
    el tipo del handler es genérico); se registra sólo para
    `RequestValidationError` (`app.py`), así que el chequeo de abajo nunca
    da `TypeError` en los hechos — queda igual, no por las dudas sino
    porque sin él `exc.errors()` no tipa (y un `assert`, que se puede
    desactivar con `-O`, no es la herramienta para esto en código de
    producción)."""
    if not isinstance(exc, RequestValidationError):
        raise TypeError(f"manejador_422 recibió un error inesperado: {type(exc)!r}")
    detalle: list[dict[str, Any]] = [
        {"type": error["type"], "loc": list(error["loc"]), "msg": _motivo(error)}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": detalle}
    )
