"""R6/R11: todas las rutas efectivas, con cualquier prefijo y montaje.

La lista pública es explícita en test_rutas_protegidas. Un montaje ASGI
opaco o un tipo desconocido fallan nombrando dónde no se pudo inspeccionar;
no se saltean rutas por carecer de methods/dependant.
"""

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.routing import _EffectiveRouteContext, _FrontendRouteGroup, _join_frontend_paths
from starlette.routing import Mount, WebSocketRoute


@dataclass(frozen=True)
class RutaEfectiva:
    path: str
    methods: frozenset[str]
    dependant: Any = None


def rutas_efectivas(app: FastAPI) -> list[RutaEfectiva]:
    rutas: list[RutaEfectiva] = []

    def recorrer(candidato: Any, prefijo: str = "", ubicacion: str = "") -> None:
        if type(candidato).__name__ == "_IncludedRouter":
            # FastAPI resuelve los prefijos de inclusión, incluidos los anidados.
            for sub in candidato.effective_candidates():
                recorrer(sub, prefijo, prefijo + candidato.include_context.prefix)
            return
        original = getattr(candidato, "original_route", candidato)
        starlette = getattr(candidato, "starlette_route", None)
        ruta = (
            getattr(candidato, "path", None)
            or getattr(starlette, "path", None)
            or getattr(original, "path", None)
        )
        if not isinstance(ruta, str):
            raise AssertionError(
                f"ruta desconocida bajo {ubicacion or prefijo or '/'}: {original!r}"
            )
        efectiva = prefijo + ruta
        if isinstance(original, Mount):
            subrutas = original.routes
            if not subrutas:
                raise AssertionError(f"montaje opaco sin rutas inspeccionables: {efectiva}")
            for sub in subrutas:
                recorrer(sub, efectiva)
            return
        metodos: set[str] | None
        if isinstance(original, WebSocketRoute):
            metodos = {"WEBSOCKET"}
        else:
            metodos = getattr(candidato, "methods", None) or getattr(original, "methods", None)
            if not metodos:
                raise AssertionError(f"ruta sin métodos inspeccionables: {efectiva}")
        rutas.append(
            RutaEfectiva(
                efectiva,
                frozenset(metodos),
                (
                    getattr(candidato, "dependant", None)
                    or getattr(starlette, "dependant", None)
                    or getattr(original, "dependant", None)
                ),
            )
        )

    for route in app.routes:
        recorrer(route)

    # RF-B-1 (revisión final, 19/10/2026): `app.frontend(...)` (y
    # `router.frontend(...)`) registran sus rutas en
    # `router._low_priority_routes`, nunca en `app.routes` — invisibles
    # para el recorrido de arriba. `_iter_low_priority_routes` entrega el
    # grupo crudo (`_FrontendRouteGroup`, sin prefijo) o, para uno montado
    # dentro de un router incluido, su `_EffectiveRouteContext` (con el
    # prefijo de inclusión ya resuelto, D8).
    for candidato in app.router._iter_low_priority_routes():
        if isinstance(candidato, _EffectiveRouteContext):
            prefijo = candidato.frontend_prefix
            grupo = candidato.original_route
        else:
            prefijo = ""
            grupo = candidato
        if not isinstance(grupo, _FrontendRouteGroup):
            raise AssertionError(f"ruta de baja prioridad desconocida: {grupo!r}")
        for frontend_route in grupo.routes:
            rutas.append(
                RutaEfectiva(
                    _join_frontend_paths(prefijo, frontend_route.path),
                    frozenset(frontend_route.methods),
                    None,
                )
            )

    return rutas


def rutas_reales_del_candado(app: FastAPI) -> set[tuple[str, str]]:
    # HEAD sólo se omite como alias de GET del mismo objeto/árbol de dependencias.
    # Una ruta exclusivamente HEAD es independiente y debe entrar al candado.
    return {
        (ruta.path, metodo)
        for ruta in rutas_efectivas(app)
        for metodo in ruta.methods
        if metodo != "HEAD" or "GET" not in ruta.methods
    }


def depende_de(app: FastAPI, ruta: str, metodo: str, objetivo: object) -> bool:
    """El árbol de la primera ruta efectiva que atiende ese método y path."""
    for sub in rutas_efectivas(app):
        if sub.path == ruta and metodo in sub.methods:
            if sub.dependant is None:
                return False
            pendientes = list(sub.dependant.dependencies)
            while pendientes:
                dep = pendientes.pop()
                if dep.call is objetivo:
                    return True
                pendientes.extend(dep.dependencies)
            return False
    return False
