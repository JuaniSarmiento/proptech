"""R6/R11: todas las rutas efectivas, con cualquier prefijo y montaje.

La lista pública es explícita en test_rutas_protegidas. Un montaje ASGI
opaco o un tipo desconocido fallan nombrando dónde no se pudo inspeccionar;
no se saltean rutas por carecer de methods/dependant.
"""

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from starlette.routing import Mount, WebSocketRoute


@dataclass(frozen=True)
class RutaEfectiva:
    path: str
    methods: frozenset[str]
    dependant: Any = None


def rutas_efectivas(app: FastAPI) -> list[RutaEfectiva]:
    rutas: list[RutaEfectiva] = []

    def recorrer(candidato: Any, prefijo: str = "") -> None:
        if type(candidato).__name__ == "_IncludedRouter":
            # FastAPI resuelve los prefijos de inclusión, incluidos los anidados.
            for sub in candidato.effective_candidates():
                recorrer(sub, prefijo)
            return
        original = getattr(candidato, "original_route", candidato)
        starlette = getattr(candidato, "starlette_route", None)
        ruta = (
            getattr(candidato, "path", None)
            or getattr(starlette, "path", None)
            or getattr(original, "path", None)
        )
        if not isinstance(ruta, str):
            raise AssertionError(f"ruta desconocida bajo {prefijo or '/'}: {candidato!r}")
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
    return rutas


def rutas_reales_del_candado(app: FastAPI) -> set[tuple[str, str]]:
    return {
        (ruta.path, metodo)
        for ruta in rutas_efectivas(app)
        for metodo in ruta.methods
        if metodo != "HEAD"
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
