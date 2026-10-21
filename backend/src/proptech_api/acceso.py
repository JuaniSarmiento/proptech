"""Token local, identidad vinculada y sesión con tenant (D1 a D3 del 2b).

Los overrides de FastAPI siguen permitiendo inyectar la identidad en tests.
Sin token válido, ninguna dependencia abre una sesión de base.
"""

import re
from collections.abc import Callable, Coroutine, Iterator
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as HTTPExceptionDeStarlette
from starlette.responses import Response

from proptech_core.acceso.aplicacion.identidad import IdentidadNoDisponible, resolver
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.token import (
    TokenInvalido,
    TokenVerificado,
    verificar_token_de_sesion,
)
from proptech_core.compartido.base_de_datos import abrir_sesion


def token_de_sesion_actual(request: Request) -> TokenVerificado:
    configuracion = getattr(request.app.state, "configuracion", None)
    valores = request.headers.getlist("authorization")
    if len(valores) != 1 or configuracion is None or configuracion.clerk_jwt_key is None:
        raise HTTPException(status_code=401)
    coincidencia = re.fullmatch(r"Bearer ([^\s,]+)", valores[0], flags=re.ASCII)
    if coincidencia is None:
        raise HTTPException(status_code=401)
    try:
        return verificar_token_de_sesion(
            coincidencia[1],
            configuracion.clerk_jwt_key,
            configuracion.clerk_partes_autorizadas,
            configuracion.clerk_emisor,
            datetime.now(UTC),
        )
    except TokenInvalido:
        raise HTTPException(status_code=401) from None


def identidad_actual(
    request: Request,
    token: TokenVerificado = Depends(token_de_sesion_actual),
) -> Identidad:
    try:
        return resolver(
            request.app.state.fabrica_de_sesiones,
            token.sub,
            request.headers.get("X-Proptech-Administracion"),
        )
    except IdentidadNoDisponible:
        raise HTTPException(status_code=401) from None


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


#: RF-B-2 (revisión final, 19/10/2026): el `detail` exacto con el que
#: FastAPI envuelve CUALQUIER excepción no-HTTPException al parsear el
#: cuerpo (`fastapi/routing.py`, `except Exception: ... HTTPException(
#: status_code=400, detail="There was an error parsing the body")`).
#: Antes, `con_identidad` sólo miraba `status_code == 400`: un endpoint
#: que levanta su propio `HTTPException(400, ...)` por un motivo de
#: dominio (nunca de parseo) hacía que la identidad se resolviera DOS
#: veces, contradiciendo D6 ("en el camino que parsea bien, la resolución
#: habitual se ejecuta una sola vez"). Comparar por el `detail` exacto,
#: no sólo por el código, distingue el 400 de parseo real del de dominio.
_DETALLE_DEL_ERROR_DE_PARSEO_DEL_CUERPO = "There was an error parsing the body"


class RutaConIdentidad(APIRoute):
    """D6: un error del parser nunca se entrega antes del 401.

    FastAPI parsea JSON antes de resolver dependencias. Si ESE parseo falla
    (nunca cualquier otro 400: RF-B-2, revisión final 19/10/2026, se compara
    por el `detail` exacto de FastAPI, no sólo por el código), se resuelve
    sólo identidad con el mismo solver (incluidos overrides y dependencias
    anidadas) antes de devolver el error. En pedidos que parsean, incluido
    un 400 que el propio endpoint levanta por un motivo de dominio, FastAPI
    resuelve todo normalmente: no se autentica dos veces ni se toca la base
    en esta barrera. Las dependencias explícitas de cada ruta siguen siendo
    obligatorias y verificadas por el barrido.
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
                    else (
                        error.status_code == 400
                        and error.detail == _DETALLE_DEL_ERROR_DE_PARSEO_DEL_CUERPO
                    )
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
