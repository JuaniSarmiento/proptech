"""Que ningún camino del candado quede sin envolver (D7, cambio 2a, cierre
de las tareas 5.2/5.3; pedido explícito de Juani al revisar el informe de
la 4.2, "apuesta 2").

Dos chequeos, no uno: (1) estructural — la lista de rutas que esto cubre
tiene que ser EXACTAMENTE la que la app registra bajo `/api` (salvo
`/api/salud`, pública a propósito); si alguien agrega una ruta nueva sin
pasar por este archivo, el conjunto ya no coincide y el test falla, sin
esperar a que alguien se acuerde de extenderlo. (2) de comportamiento — cada
ruta no pública, llamada sin ninguna identidad, da 401 sin tocar la base
(ya probado en 4.2 por separado, repetido acá sobre el conjunto completo); y
llamada con una identidad real pero SIN ninguna fila en `asignacion_rol`,
nunca da 200/201 contra un recurso real (ni por falta de alcance ni por
falta de permiso: cualquiera de los dos caminos tiene que cortar).

Contenedor propio (L-006; mismo motivo que 4.1/4.2/5.2/5.3).
"""

import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_rutas"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"

#: Pública a propósito: no pasa por identidad ni por tenant (D11).
_RUTAS_PUBLICAS = {("/api/salud", "GET")}

#: Las rutas del candado que este archivo prueba, una por una, más abajo.
#: Si `_rutas_reales_del_candado()` devuelve algo que no está acá, el test
#: estructural falla nombrándolo: es la señal de que una ruta nueva no pasó
#: por este archivo.
_RUTAS_CUBIERTAS = {
    ("/api/complejos/{complejo_id}", "GET"),
    ("/api/unidades/{unidad_id}", "GET"),
    ("/api/complejos/{complejo_id}/asignaciones", "POST"),
}


def _conectar(contenedor: PostgresContainer, usuario: str, password: str) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario,
        password=password,
        dbname=contenedor.dbname,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def contenedor() -> Iterator[PostgresContainer]:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as iniciado:
        yield iniciado


def _entorno_de_roles(contenedor: PostgresContainer) -> dict[str, str]:
    import os

    return {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD,
        "POSTGRES_APP_USER": APP_USER,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD,
        "POSTGRES_RESPALDO_USER": RESPALDO_USER,
        "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD,
    }


def _alembic_env(contenedor: PostgresContainer) -> dict[str, str]:
    entorno = dict(_entorno_de_roles(contenedor))
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _correr(args: list[str], entorno: dict[str, str]) -> None:
    subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    try:
        yield
    finally:
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


@pytest.fixture(scope="module")
def mundo(contenedor: PostgresContainer, esquema: None) -> dict[str, Any]:
    """Un complejo y una unidad reales, más una persona SIN ninguna fila en
    `asignacion_rol`: ni alcanza ni puede nada, aunque tenga una identidad
    válida de esta misma administración."""
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    with conexion.cursor() as cur:
        admin_id = uuid.uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
        cur.execute("INSERT INTO administracion (id, nombre) VALUES (%s, %s)", (str(admin_id), "A"))
        complejo_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO complejo (id, administracion_id, nombre) VALUES (%s, %s, %s)",
            (str(complejo_id), str(admin_id), "Complejo"),
        )
        unidad_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO unidad (id, administracion_id, complejo_id, nombre) "
            "VALUES (%s, %s, %s, %s)",
            (str(unidad_id), str(admin_id), str(complejo_id), "1A"),
        )
        persona_sin_asignacion = uuid.uuid4()
        cur.execute(
            "INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
            (str(persona_sin_asignacion), str(admin_id), "sin asignación", "sin-asig@ej.com"),
        )
        otra_persona = uuid.uuid4()
        cur.execute(
            "INSERT INTO persona (id, administracion_id, nombre, email) VALUES (%s, %s, %s, %s)",
            (str(otra_persona), str(admin_id), "destinatario", "destinatario@ej.com"),
        )
        # Ninguna fila en asignacion_rol para persona_sin_asignacion: a propósito.
    conexion.close()
    return {
        "administracion_id": admin_id,
        "complejo_id": complejo_id,
        "unidad_id": unidad_id,
        "persona_sin_asignacion": persona_sin_asignacion,
        "otra_persona": otra_persona,
    }


@pytest.fixture
def app_real(
    contenedor: PostgresContainer, esquema: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Iterator[FastAPI]:
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "x")
    ruta_parametros = tmp_path / "parametros.yaml"
    raiz = RAIZ_BACKEND.parent
    ruta_parametros.write_text((raiz / "config" / "parametros.yaml").read_text())
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta_parametros))

    from proptech_api.app import crear_app

    app = crear_app()
    with TestClient(app):
        yield app


@pytest.fixture
def cliente(app_real: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_real) as cliente:
        yield cliente


def _api_routes(app: FastAPI) -> list[Any]:
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
    `_EffectiveRouteContext`): el resto del archivo sólo usa `.path`,
    `.methods` y `.dependant`, que los dos exponen.
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


def _rutas_reales_del_candado(app: FastAPI) -> set[tuple[str, str]]:
    rutas: set[tuple[str, str]] = set()
    for sub in _api_routes(app):
        for metodo in sub.methods or set():
            if metodo != "HEAD":
                rutas.add((sub.path, metodo))
    return rutas


def _depende_de(app: FastAPI, ruta: str, metodo: str, objetivo: object) -> bool:
    """Si `objetivo` aparece en el árbol de dependencias de esa ruta,
    directo o anidado (no sólo las de primer nivel)."""
    for sub in _api_routes(app):
        if sub.path == ruta and metodo in (sub.methods or set()):
            pendientes = list(sub.dependant.dependencies)
            while pendientes:
                dep = pendientes.pop()
                if dep.call is objetivo:
                    return True
                pendientes.extend(dep.dependencies)
    return False


# --- Estructural: ninguna ruta nueva se queda afuera de este archivo ---


def test_las_rutas_del_candado_son_exactamente_las_cubiertas_acá(app_real: FastAPI) -> None:
    rutas_reales = _rutas_reales_del_candado(app_real) - _RUTAS_PUBLICAS
    assert rutas_reales == _RUTAS_CUBIERTAS, (
        f"rutas no cubiertas por este archivo: {rutas_reales - _RUTAS_CUBIERTAS}; "
        f"cubiertas pero ya no existen: {_RUTAS_CUBIERTAS - rutas_reales}"
    )


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
def test_cada_ruta_del_candado_depende_de_identidad_actual(
    app_real: FastAPI, ruta_y_metodo: tuple[str, str]
) -> None:
    ruta, metodo = ruta_y_metodo
    assert _depende_de(app_real, ruta, metodo, identidad_actual), (
        f"{metodo} {ruta} no depende de identidad_actual"
    )


# --- De comportamiento: sin identidad, 401; con identidad sin ninguna asignación, nunca 200/201 ---


def _pedido(cliente: TestClient, ruta: str, metodo: str, mundo: dict[str, Any]) -> Any:
    ruta_resuelta = ruta.format(complejo_id=mundo["complejo_id"], unidad_id=mundo["unidad_id"])
    if metodo == "GET":
        return cliente.get(ruta_resuelta)
    return cliente.post(
        ruta_resuelta,
        json={"persona_id": str(mundo["otra_persona"]), "rol": "consejo"},
    )


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
def test_cada_ruta_sin_identidad_da_401(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any], ruta_y_metodo: tuple[str, str]
) -> None:
    ruta, metodo = ruta_y_metodo
    respuesta = _pedido(cliente, ruta, metodo, mundo)
    assert respuesta.status_code == 401, f"{metodo} {ruta}: {respuesta.status_code}"


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
def test_cada_ruta_con_identidad_sin_asignacion_nunca_da_200_ni_201(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any], ruta_y_metodo: tuple[str, str]
) -> None:
    ruta, metodo = ruta_y_metodo
    app_real.dependency_overrides[identidad_actual] = lambda: Identidad(
        administracion_id=mundo["administracion_id"],
        persona_id=mundo["persona_sin_asignacion"],
    )
    try:
        respuesta = _pedido(cliente, ruta, metodo, mundo)
        assert respuesta.status_code not in (200, 201), (
            f"{metodo} {ruta}: una identidad sin ninguna asignación tuvo éxito "
            f"({respuesta.status_code})"
        )
        assert respuesta.status_code in (403, 404), respuesta.status_code
    finally:
        app_real.dependency_overrides.pop(identidad_actual, None)


# --- D8/R6: el barrido ve la ruta efectiva, sin depender de cómo se montó ---


def test_ruta_montada_con_prefijo_de_inclusion_sin_cubrir_se_detecta() -> None:
    """Scenario `autorizacion-por-rol` > Ruta montada con prefijo de
    inclusión: un router SIN prefijo propio, incluido con
    `include_router(prefix="/api")`, con una ruta fuera de
    `_RUTAS_CUBIERTAS`. El defecto (D8): el barrido miraba
    `original_router.routes`, cuyo `.path` no lleva el prefijo de inclusión
    ("/sin-cubrir", no "/api/sin-cubrir"), así que ni pasaba el filtro
    `startswith("/api")` y la ruta quedaba invisible — no "detectada pero sin
    cubrir", sino afuera del conjunto entero. Si el barrido real corriera
    sobre una app así, tendría que fallar nombrando la ruta."""
    app = FastAPI()
    router = APIRouter()

    @router.get("/sin-cubrir")
    def _sin_cubrir() -> dict[str, str]:  # pragma: no cover - nunca se llama
        return {}

    app.include_router(router, prefix="/api")

    rutas = _rutas_reales_del_candado(app)

    assert ("/api/sin-cubrir", "GET") in rutas, (
        "el barrido no vio la ruta montada con include_router(prefix=...): "
        f"rutas detectadas: {rutas}"
    )
    assert rutas - _RUTAS_PUBLICAS != _RUTAS_CUBIERTAS


def test_ruta_agregada_directo_a_la_app_sin_cubrir_se_detecta() -> None:
    """Scenario `autorizacion-por-rol` > Ruta agregada directo a la app: una
    ruta sumada con `add_api_route` sobre la app misma (sin pasar por ningún
    router), fuera de `_RUTAS_CUBIERTAS`. El defecto (D8): el barrido sólo
    miraba rutas envueltas en `_IncludedRouter`
    (`type(route).__name__ != "_IncludedRouter": continue`), así que una
    `APIRoute` agregada directo a `app.routes` nunca entraba al recorrido."""
    app = FastAPI()
    app.add_api_route("/api/directo-sin-cubrir", lambda: {}, methods=["GET"])

    rutas = _rutas_reales_del_candado(app)

    assert ("/api/directo-sin-cubrir", "GET") in rutas, (
        "el barrido no vio la ruta agregada con add_api_route directo a la app: "
        f"rutas detectadas: {rutas}"
    )
    assert rutas - _RUTAS_PUBLICAS != _RUTAS_CUBIERTAS
