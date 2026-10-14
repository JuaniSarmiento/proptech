"""Middleware ASGI puro que asigna o valida el `request_id` de cada pedido,
lo devuelve en `X-Request-ID` y loguea `pedido_atendido` al final (D8).

ASGI puro (no `BaseHTTPMiddleware`) para no perder la `ContextVar` entre el
pedido y el endpoint cuando éste corre en el pool de hilos.
"""

import json
import logging
import time
import uuid

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from proptech_core.compartido.logs import datos_de_excepcion
from proptech_core.compartido.seguimiento import request_id_actual, validar_request_id

#: Largo al que se trunca el path crudo cuando ninguna ruta coincidió (no hay
#: `scope["route"]` para tomar la plantilla). Nunca incluye la query string.
LARGO_MAXIMO_RUTA_SIN_COINCIDENCIA = 200

_logger = logging.getLogger("proptech_api.seguimiento")


def _ruta_de(scope: Scope) -> str:
    """La plantilla de la ruta que coincidió (`/api/unidades/{id}`), con el
    prefijo del router incluido. Nunca del valor concreto del path:
    reemplazar el valor sobre el path (el intento original) filtra el dato
    si es prefijo de otro segmento, o si el convertidor (`int`, `uuid`) lo
    cambió y el valor original ya no aparece en el path. Sin coincidencia,
    el path crudo truncado y sin query string.

    `scope["route"].path_format` (lo que se usaba hasta la vuelta 2) sólo
    trae la ruta **relativa al router que la declara** (F3, vuelta 3): con
    `include_router(prefix=...)` o un router anidado (el patrón de "routers
    por dominio"), FastAPI 0.143 resuelve el prefijo de forma perezosa y no
    lo funde en `path_format` del `APIRoute` original. La ruta YA fundida
    con el prefijo (y la que de hecho matcheó) vive en
    `scope["fastapi"]["effective_route_context"].path_format`: FastAPI la
    calcula una vez por combinación de router y la cachea ahí. Si esa clave
    no está (una ruta declarada directo en `app`, sin pasar por un router
    incluido con prefijo), `path_format` del route ya trae el camino
    completo y alcanza."""
    ruta = scope.get("route")
    if ruta is None:
        return str(scope["path"])[:LARGO_MAXIMO_RUTA_SIN_COINCIDENCIA]
    datos_fastapi = scope.get("fastapi")
    if isinstance(datos_fastapi, dict):
        contexto_efectivo = datos_fastapi.get("effective_route_context")
        path_format_efectivo = getattr(contexto_efectivo, "path_format", None)
        if isinstance(path_format_efectivo, str):
            return path_format_efectivo
    return str(ruta.path_format)


class MiddlewareSeguimiento:
    """Middleware ASGI puro: ver el docstring del módulo."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        encabezados = Headers(scope=scope)
        # `Headers.get` de Starlette devuelve sólo el PRIMER valor si el
        # cliente mandó `X-Request-ID` repetido; el `Headers` del fetch de
        # la web (y de cualquier cliente que siga el estándar) los une con
        # coma (L-009, gemelo de `web/src/lib/seguimiento.ts`). Unirlos acá
        # también hace que la API rechace (no es un UUID canónico) exactamente
        # los mismos casos que la web, en vez de tomar "el primero que llegó"
        # como si fuera el único (F9, vuelta 2 de 1c).
        valores = encabezados.getlist("x-request-id")
        crudo = ", ".join(valores) if valores else None
        validado = validar_request_id(crudo) if crudo is not None else None
        request_id = validado or str(uuid.uuid4())

        token = request_id_actual.set(request_id)
        estado_capturado: dict[str, int | None] = {"estado": None}

        async def send_envuelto(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                encabezados_respuesta = list(mensaje.get("headers", []))
                encabezados_respuesta.append((b"x-request-id", request_id.encode("ascii")))
                mensaje["headers"] = encabezados_respuesta
                estado_capturado["estado"] = mensaje["status"]
            await send(mensaje)

        inicio = time.monotonic()
        try:
            await self.app(scope, receive, send_envuelto)
        except Exception as excepcion:
            # Ningún error no atrapado (propio o de un tercero: psycopg,
            # SQLAlchemy) llega a la respuesta ni a los logs con su mensaje
            # (D13, L-007): sólo tipo y ubicación, nunca `str(excepcion)`.
            _logger.error("error_inesperado", extra=datos_de_excepcion(excepcion))
            if estado_capturado["estado"] is None:
                cuerpo = json.dumps({"error": "interno", "request_id": request_id}).encode("utf-8")
                await send_envuelto(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send_envuelto({"type": "http.response.body", "body": cuerpo})
            else:
                raise
        finally:
            duracion_ms = round((time.monotonic() - inicio) * 1000)
            _logger.info(
                "pedido_atendido",
                extra={
                    "metodo": scope["method"],
                    "ruta": _ruta_de(scope),
                    "estado": estado_capturado["estado"],
                    "duracion_ms": duracion_ms,
                },
            )
            request_id_actual.reset(token)
