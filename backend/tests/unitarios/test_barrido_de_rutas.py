"""R6/D8: rutas efectivas fuera de /api, montadas y de otros protocolos."""

import pytest
from fastapi import APIRouter, Depends, FastAPI, WebSocket
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from proptech_api.acceso import identidad_actual
from tests.integracion._barrido_de_rutas import depende_de, rutas_reales_del_candado
from tests.integracion.test_rutas_protegidas import _RUTAS_PUBLICAS


def test_barrido_ve_una_ruta_sin_guarda_fuera_de_api() -> None:
    """Spec: "El barrido de rutas protegidas SHALL ver toda ruta que la app
    registra, sin depender de cómo se montó". `rutas_efectivas` filtra por
    `startswith("/api")`: una ruta de dominio sin identidad montada en otro
    prefijo (p.ej. `/interno`) no entra al conjunto, el test estructural
    sigue verde y la ruta queda abierta."""
    app = FastAPI()

    @app.get("/interno/unidades")
    def _sin_guarda() -> dict[str, str]:  # pragma: no cover - nunca se llama
        return {}

    rutas = rutas_reales_del_candado(app) - _RUTAS_PUBLICAS
    assert ("/interno/unidades", "GET") in rutas, f"el barrido no la ve: {rutas}"


def test_barrido_falla_nombrando_una_subapp_montada_bajo_api() -> None:
    """Spec: "la suite de tests falla nombrando esa ruta". Una sub-app con
    `app.mount("/api/v2", ...)` hace explotar el barrido con
    `AttributeError: 'Mount' object has no attribute 'methods'`: falla, pero
    sin nombrar ninguna ruta."""
    app = FastAPI()
    sub = FastAPI()

    @sub.get("/unidades")
    def _sin_guarda() -> dict[str, str]:  # pragma: no cover - nunca se llama
        return {}

    app.mount("/api/v2", sub)
    try:
        rutas = rutas_reales_del_candado(app)
    except AttributeError as error:
        pytest.fail(f"el barrido revienta sin nombrar la ruta: {error!r}")
    assert ("/api/v2/unidades", "GET") in rutas


@pytest.mark.parametrize("prefijo", ["/interno", "/gestion/v3", ""])
def test_barrido_recursivo_de_routers_y_subapps_con_dependencia(prefijo: str) -> None:
    app = FastAPI()
    sub = FastAPI()
    hoja = FastAPI()
    router = APIRouter()
    router.add_api_route(
        "/unidades", lambda: {}, methods=["GET"], dependencies=[Depends(identidad_actual)]
    )
    hoja.include_router(router, prefix="/padron")
    sub.mount("/hijo", hoja)
    app.mount(prefijo or "/raiz", sub)
    efectiva = (prefijo or "/raiz") + "/hijo/padron/unidades"
    assert (efectiva, "GET") in rutas_reales_del_candado(app)
    assert depende_de(app, efectiva, "GET", identidad_actual)


def test_websocket_y_ruta_starlette_se_detectan_sin_inventar_dependencias() -> None:
    app = FastAPI()

    @app.websocket("/interno/eventos")
    async def eventos(websocket: WebSocket) -> None:
        await websocket.close()

    app.router.routes.append(Route("/interno/http", lambda request: None))
    rutas = rutas_reales_del_candado(app)
    assert ("/interno/eventos", "WEBSOCKET") in rutas
    assert ("/interno/http", "GET") in rutas
    assert not depende_de(app, "/interno/http", "GET", identidad_actual)
    assert not depende_de(app, "/interno/eventos", "WEBSOCKET", identidad_actual)


def test_mount_opaco_falla_nombrando_su_ruta() -> None:
    app = FastAPI()

    async def opaca(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    app.mount("/interno/opaco", opaca)
    with pytest.raises(AssertionError, match="/interno/opaco"):
        rutas_reales_del_candado(app)


def test_mount_en_router_incluido_y_websocket_con_guarda() -> None:
    app = FastAPI()
    sub = FastAPI()
    router_ws = APIRouter(dependencies=[Depends(identidad_actual)])

    @router_ws.websocket("/eventos")
    async def eventos(websocket: WebSocket) -> None:
        await websocket.close()

    sub.include_router(router_ws, prefix="/vivo")
    router = APIRouter()
    router.mount("/padron", sub)
    app.include_router(router, prefix="/interno")
    ruta = "/interno/padron/vivo/eventos"
    assert (ruta, "WEBSOCKET") in rutas_reales_del_candado(app)
    assert depende_de(app, ruta, "WEBSOCKET", identidad_actual)


def test_head_sin_get_es_una_ruta_que_el_candado_debe_ver() -> None:
    app = FastAPI()
    app.add_api_route("/interno/solo-cabecera", lambda: {}, methods=["HEAD"])
    assert ("/interno/solo-cabecera", "HEAD") in rutas_reales_del_candado(app)


def test_ruta_desconocida_dentro_de_include_falla_nombrando_el_prefijo() -> None:
    from starlette.routing import Host

    app = FastAPI()
    router = APIRouter()
    router.routes.append(Host("interno.ejemplo.invalid", app=FastAPI()))
    app.include_router(router, prefix="/gestion")
    with pytest.raises(AssertionError, match="/gestion"):
        rutas_reales_del_candado(app)
