"""Identidad inyectable y la sesión con tenant (D7, cambio 2a).

`identidad_actual` responde siempre 401, sin tocar la base: hasta el cambio
2b (el login) nadie se puede autenticar de verdad. Los tests la reemplazan
con `app.dependency_overrides[identidad_actual]`.
"""

from collections.abc import Callable, Coroutine, Iterator
from contextlib import AsyncExitStack
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as HTTPExceptionDeStarlette
from starlette.responses import Response

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import abrir_sesion


def identidad_actual() -> Identidad:
    raise HTTPException(status_code=401)


def sesion_con_tenant(
    request: Request, identidad: Identidad = Depends(identidad_actual)
) -> Iterator[Session]:
    """Depende EXPLÍCITAMENTE de la identidad (D7): así FastAPI no abre la
    sesión antes de saber quién es — si `identidad_actual` levanta 401, esta
    dependencia nunca llega a correr su cuerpo, y ninguna sentencia toca la
    base. El tenant sale sólo de `identidad.administracion_id` (D4): nunca
    de un encabezado, un parámetro o un campo del cuerpo del pedido, aunque
    alguno se llame igual. Como el tenant viaja en `session.info`, da igual
    si esta dependencia es sincrónica o `async def` (D4, punto 5 del
    arquitecto).
    """
    sesion = abrir_sesion(request.app.state.fabrica_de_sesiones, identidad.administracion_id)
    try:
        yield sesion
    finally:
        sesion.close()


def _exigir_identidad(identidad: Identidad = Depends(identidad_actual)) -> None:
    """Árbol reducido: sólo identidad, nunca sesión ni SQL de dominio."""


class RutaConIdentidad(APIRoute):
    """D6: un error del parser nunca se entrega antes del 401.

    FastAPI parsea JSON antes de resolver dependencias. Si ese parseo falla,
    se resuelve sólo identidad con el mismo solver (incluidos overrides y
    dependencias anidadas) antes de devolver el error. En pedidos que parsean,
    FastAPI resuelve todo normalmente: no se autentica dos veces ni se toca
    la base en esta barrera. Las dependencias explícitas de cada ruta siguen
    siendo obligatorias y verificadas por el barrido.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()
        guarda = get_dependant(path=self.path_format, call=_exigir_identidad)

        async def con_identidad(request: Request) -> Response:
            try:
                return await handler(request)
            except (RequestValidationError, HTTPExceptionDeStarlette) as error:
                fallo_de_parseo = (
                    any(e["type"] == "json_invalid" for e in error.errors())
                    if isinstance(error, RequestValidationError)
                    else error.status_code == 400
                )
                if fallo_de_parseo:
                    async with AsyncExitStack() as pila:
                        resuelto = await solve_dependencies(
                            request=request,
                            dependant=guarda,
                            dependency_overrides_provider=request.app,
                            async_exit_stack=pila,
                            embed_body_fields=False,
                        )
                        if resuelto.errors:
                            raise RequestValidationError(resuelto.errors) from None
                raise

        return con_identidad
