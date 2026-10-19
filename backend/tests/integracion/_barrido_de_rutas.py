"""Barrido de rutas EFECTIVAS de la app bajo `/api` (D8, R6).

Compartido entre `test_rutas_protegidas.py` (2.1, el candado) y
`test_altas_sin_id_del_cliente.py` (2.2, R11): los dos necesitan la misma
noción de "qué rutas tiene la app de verdad", y que sea la MISMA función
evita que diverjan (L-009: el arreglo se prueba en el gemelo, mismo criterio
aplicado acá a dos lectores del mismo barrido). No es un archivo de test (no
empieza con `test_`): pytest no lo recolecta.
"""

from typing import Any

from fastapi import FastAPI


def rutas_efectivas(app: FastAPI) -> list[Any]:
    """Toda ruta que la app de verdad atiende bajo `/api`, con su ruta
    EFECTIVA (prefijo de inclusión ya aplicado) — no la `APIRoute` original
    del router, que no lo lleva (D8, R6).

    Tres formas de llegar a una ruta, las tres contempladas:

    - directa (`app.add_api_route(...)`): queda como `APIRoute` en
      `app.routes`, sin envolver.
    - incluida (`app.include_router(router, prefix=...)`, con o sin
      prefijo): en esta versión de FastAPI, `include_router` envuelve el
      router en un `_IncludedRouter` sin tipo público; su `.original_router`
      tiene las rutas SIN el prefijo de inclusión (por eso el barrido
      anterior, que miraba ahí, era ciego a cualquier ruta montada con
      prefijo: "/x" nunca empieza con "/api", aunque la app responda en
      "/api/x"). La ruta efectiva sale de
      `_IncludedRouter.effective_candidates()`, que arma FastAPI resolviendo
      el prefijo; cada candidato es un `_EffectiveRouteContext` (con `.path`
      ya prefijado, `.methods` y `.dependant`, igual que una `APIRoute`) o,
      si el router incluido a su vez incluye otro, un `_IncludedRouter`
      anidado — de ahí la recursión.
    - anidada (un router que incluye a otro, cualquier profundidad): se
      resuelve recursando sobre cada `_IncludedRouter` que aparece dentro de
      `effective_candidates()`, acumulando los prefijos de cada nivel (lo
      hace FastAPI; acá sólo se recorre el resultado).

    Devuelve objetos heterogéneos a propósito (`APIRoute` o
    `_EffectiveRouteContext`): quien llama sólo usa `.path`, `.methods` y
    `.dependant`, que los dos exponen.
    """
    rutas: list[Any] = []

    def _recorrer(candidato: object) -> None:
        if type(candidato).__name__ == "_IncludedRouter":
            for sub in candidato.effective_candidates():  # type: ignore[attr-defined]
                _recorrer(sub)
            return
        ruta = getattr(candidato, "path", None)
        if isinstance(ruta, str) and ruta.startswith("/api"):
            rutas.append(candidato)

    for route in app.routes:
        _recorrer(route)
    return rutas


def rutas_reales_del_candado(app: FastAPI) -> set[tuple[str, str]]:
    rutas: set[tuple[str, str]] = set()
    for sub in rutas_efectivas(app):
        for metodo in sub.methods or set():
            if metodo != "HEAD":
                rutas.add((sub.path, metodo))
    return rutas


def depende_de(app: FastAPI, ruta: str, metodo: str, objetivo: object) -> bool:
    """Si `objetivo` aparece en el árbol de dependencias de esa ruta,
    directo o anidado (no sólo las de primer nivel)."""
    for sub in rutas_efectivas(app):
        if sub.path == ruta and metodo in (sub.methods or set()):
            pendientes = list(sub.dependant.dependencies)
            while pendientes:
                dep = pendientes.pop()
                if dep.call is objetivo:
                    return True
                pendientes.extend(dep.dependencies)
    return False
