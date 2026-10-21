"""Que ningún camino del candado quede sin envolver (D7, cambio 2a, cierre
de las tareas 5.2/5.3; pedido explícito de Juani al revisar el informe de
la 4.2, "apuesta 2").

Dos chequeos, no uno: (1) estructural — la lista de rutas que esto cubre
tiene que ser EXACTAMENTE la que la app registra bajo `/api` (salvo
`/api/salud`, pública a propósito); si alguien agrega una ruta nueva sin
pasar por este archivo, el conjunto ya no coincide y el test falla, sin
esperar a que alguien se acuerde de extenderlo. (2) de comportamiento — cada
ruta no pública, llamada sin ninguna identidad, da 401 SIN TOCAR LA BASE,
sobre el conjunto completo de `_RUTAS_CUBIERTAS` (RF-B-3, revisión final
19/10/2026: hasta acá esto sólo miraba el status, y "sin tocar la base"
vivía repartido en los `..._401_sin_sql` de otros archivos, sobre
subconjuntos — el docstring lo prometía sobre el conjunto completo sin
cumplirlo; ahora instrumenta `before_cursor_execute` del engine real por
cada ruta, mismo mecanismo que esos archivos); y llamada con una identidad
real pero SIN ninguna fila en `asignacion_rol`, nunca da 200/201 contra un
recurso real (ni por falta de alcance ni por falta de permiso: cualquiera
de los dos caminos tiene que cortar).

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
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from proptech_api.acceso import identidad_actual, token_de_sesion_actual
from proptech_core.acceso.dominio.identidad import Identidad

from ._barrido_de_rutas import depende_de as _depende_de
from ._barrido_de_rutas import rutas_reales_del_candado as _rutas_reales_del_candado

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
_RUTAS_PUBLICAS = {
    ("/api/salud", "GET"),
}
_RUTAS_DOCUMENTACION = {
    ("/docs", "GET"),
    ("/docs/oauth2-redirect", "GET"),
    ("/redoc", "GET"),
    ("/openapi.json", "GET"),
}

#: Las rutas del candado que este archivo prueba, una por una, más abajo.
#: Si `_rutas_reales_del_candado()` devuelve algo que no está acá, el test
#: estructural falla nombrándolo: es la señal de que una ruta nueva no pasó
#: por este archivo.
_RUTAS_CON_TOKEN = {("/api/sesion", "GET"), ("/api/invitaciones/aceptar", "POST")}

_RUTAS_CUBIERTAS = {
    ("/api/personal/invitaciones", "POST"),
    ("/api/invitaciones/aceptar", "POST"),
    ("/api/sesion", "GET"),
    ("/api/sesion/ingreso", "POST"),
    ("/api/complejos/{complejo_id}/categorias", "GET"),
    ("/api/complejos/{complejo_id}/categorias", "POST"),
    ("/api/categorias/{categoria_id}", "PATCH"),
    ("/api/complejos/{complejo_id}/categorias/orden", "PUT"),
    ("/api/complejos/{complejo_id}/configuracion", "GET"),
    ("/api/complejos/{complejo_id}/configuracion/versiones", "GET"),
    ("/api/complejos/{complejo_id}/configuracion/versiones", "POST"),
    ("/api/complejos/{complejo_id}/unidades", "GET"),
    ("/api/complejos/{complejo_id}/unidades", "POST"),
    ("/api/unidades/{unidad_id}", "PATCH"),
    ("/api/complejos/{complejo_id}/grupos", "GET"),
    ("/api/complejos/{complejo_id}/grupos", "POST"),
    ("/api/grupos/{grupo_id}", "PATCH"),
    ("/api/grupos/{grupo_id}/unidades", "PUT"),
    ("/api/complejos", "GET"),
    ("/api/complejos", "POST"),
    ("/api/complejos/{complejo_id}/resumen", "GET"),
    ("/api/complejos/{complejo_id}/estado-de-migracion/sin-saldos-previos", "POST"),
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
            "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
            "VALUES (%s, %s, %s, 'Mendoza')",
            (str(complejo_id), str(admin_id), "Complejo"),
        )
        unidad_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO unidad (id, administracion_id, complejo_id, identificador, "
            "tipo, piso, coeficiente, superficie_m2) "
            "VALUES (%s, %s, %s, %s, 'departamento', '1', '0.1', '60.00')",
            (str(unidad_id), str(admin_id), str(complejo_id), "1A"),
        )
        grupo_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO grupo_de_reparto "
            "(id, administracion_id, complejo_id, clave, nombre, metodo) "
            "VALUES (%s, %s, %s, 'ascensor', 'Ascensor', 'coeficiente')",
            (grupo_id, admin_id, complejo_id),
        )
        persona_sin_asignacion = uuid.uuid4()
        categoria_id = uuid.uuid4()
        cur.execute(
            "INSERT INTO categoria_de_gasto (id, administracion_id, complejo_id, clave, "
            "nombre, orden) VALUES (%s, %s, %s, 'limpieza', 'Limpieza', 0)",
            (categoria_id, admin_id, complejo_id),
        )
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
        "grupo_id": grupo_id,
        "categoria_id": categoria_id,
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


# --- Estructural: ninguna ruta nueva se queda afuera de este archivo ---


def test_las_rutas_del_candado_son_exactamente_las_cubiertas_acá(app_real: FastAPI) -> None:
    rutas_reales = _rutas_reales_del_candado(app_real) - _RUTAS_PUBLICAS - _RUTAS_DOCUMENTACION
    assert rutas_reales == _RUTAS_CUBIERTAS, (
        f"rutas no cubiertas por este archivo: {rutas_reales - _RUTAS_CUBIERTAS}; "
        f"cubiertas pero ya no existen: {_RUTAS_CUBIERTAS - rutas_reales}"
    )


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
def test_cada_ruta_del_candado_depende_de_identidad_actual(
    app_real: FastAPI, ruta_y_metodo: tuple[str, str]
) -> None:
    ruta, metodo = ruta_y_metodo
    guarda = token_de_sesion_actual if (ruta, metodo) in _RUTAS_CON_TOKEN else identidad_actual
    assert _depende_de(app_real, ruta, metodo, guarda), (
        f"{metodo} {ruta} no depende de identidad_actual"
    )


# --- De comportamiento: sin identidad, 401; con identidad sin ninguna asignación, nunca 200/201 ---


def _pedido(cliente: TestClient, ruta: str, metodo: str, mundo: dict[str, Any]) -> Any:
    ruta_resuelta = ruta.format(**mundo)
    if metodo == "GET":
        return cliente.get(ruta_resuelta)
    if "/configuracion/versiones" in ruta:
        from .test_configuracion_api import version

        return cliente.post(ruta_resuelta, json=version())
    if "/categorias" in ruta:
        cuerpo_categoria: dict[str, Any] = (
            {"orden": [str(mundo["categoria_id"])]} if metodo == "PUT" else {"nombre": "Nueva"}
        )
        if metodo == "POST":
            cuerpo_categoria["clave"] = "nueva"
        return cliente.request(metodo, ruta_resuelta, json=cuerpo_categoria)
    if ruta == "/api/complejos":
        return cliente.post(ruta_resuelta, json={"nombre": "Edificio", "localidad": "Mendoza"})
    if ruta.endswith("/sin-saldos-previos"):
        return cliente.post(ruta_resuelta)
    if ruta.endswith("/unidades") or ruta == "/api/unidades/{unidad_id}":
        cuerpo = (
            {"modo_de_coeficientes": "renormalizado", "unidades": []}
            if metodo == "PUT"
            else {
                "identificador": "2A",
                "tipo": "departamento",
                "piso": "2",
                "coeficiente": "0.2",
                "superficie_m2": "60.00",
            }
        )
        return cliente.request(metodo, ruta_resuelta, json=cuerpo)
    if "/grupos" in ruta:
        return cliente.request(
            metodo,
            ruta_resuelta,
            json={"clave": "cocheras", "nombre": "Cocheras", "metodo": "coeficiente"},
        )
    return cliente.post(
        ruta_resuelta,
        json={"persona_id": str(mundo["otra_persona"]), "rol": "consejo"},
    )


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
def test_cada_ruta_sin_identidad_da_401(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any], ruta_y_metodo: tuple[str, str]
) -> None:
    """RF-B-3 (revisión final, 19/10/2026): el docstring de este archivo
    prometía "sin tocar la base" sobre el conjunto COMPLETO de rutas, pero
    hasta acá sólo miraba el status — la instrumentación de SQL vivía
    repartida en `..._401_sin_sql` de otros archivos, sobre subconjuntos.
    Mismo mecanismo que `test_edificios_api.test_401_sin_sql_incluso_con_
    cuerpo_invalido`: escuchar `before_cursor_execute` del engine real."""
    from sqlalchemy import event

    ruta, metodo = ruta_y_metodo
    sentencias: list[Any] = []

    def registrar(*args: Any) -> None:
        sentencias.append(args[2])

    event.listen(app_real.state.engine, "before_cursor_execute", registrar)
    try:
        respuesta = _pedido(cliente, ruta, metodo, mundo)
    finally:
        event.remove(app_real.state.engine, "before_cursor_execute", registrar)
    assert respuesta.status_code == 401, f"{metodo} {ruta}: {respuesta.status_code}"
    assert sentencias == [], f"{metodo} {ruta} tocó la base sin identidad: {sentencias}"


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
def test_cada_ruta_con_identidad_sin_asignacion_nunca_da_200_ni_201(
    cliente: TestClient, app_real: FastAPI, mundo: dict[str, Any], ruta_y_metodo: tuple[str, str]
) -> None:
    ruta, metodo = ruta_y_metodo
    if ruta.startswith("/api/sesion") or (ruta, metodo) in _RUTAS_CON_TOKEN:
        # Estas rutas comprueban el vínculo real, sin el override de dominio.
        respuesta = _pedido(cliente, ruta, metodo, mundo)
        assert respuesta.status_code == 401
        return
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
    assert rutas - _RUTAS_PUBLICAS - _RUTAS_DOCUMENTACION - _RUTAS_CUBIERTAS == {
        ("/api/sin-cubrir", "GET")
    }


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
    assert rutas - _RUTAS_PUBLICAS - _RUTAS_DOCUMENTACION - _RUTAS_CUBIERTAS == {
        ("/api/directo-sin-cubrir", "GET")
    }


# --- RF-B-3 (revisión final, 19/10/2026): el barrido de SQL puede fallar ---


def test_mutante_ruta_que_toca_la_base_antes_de_la_identidad_hace_fallar_el_barrido() -> None:
    """L-019: `sentencias == []` en `test_cada_ruta_sin_identidad_da_401`
    nace verde sobre las rutas reales (D7 ya las hace bien) — nunca se vio
    fallar. Acá se arma, a mano, la ruta que esa regla existe para
    detectar: una dependencia que ejecuta SQL ANTES que `identidad_actual`
    (`_toca_la_base`, declarada primero en la firma). El mismo mecanismo
    de instrumentación (`before_cursor_execute`) tiene que ver esa
    sentencia y hacer fallar la aserción que el test real usa."""
    from sqlalchemy import create_engine, event, text

    app = FastAPI()
    engine = create_engine("sqlite://")

    def _toca_la_base() -> None:
        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))

    @app.get("/mutante")
    def _ruta_rota(
        _tocada: None = Depends(_toca_la_base),
        _identidad: Identidad = Depends(identidad_actual),
    ) -> dict[str, str]:  # pragma: no cover - nunca se llega, identidad_actual da 401 siempre
        return {}

    cliente = TestClient(app)
    sentencias: list[object] = []

    def registrar(*args: object) -> None:
        sentencias.append(args[2])

    event.listen(engine, "before_cursor_execute", registrar)
    try:
        respuesta = cliente.get("/mutante")
    finally:
        event.remove(engine, "before_cursor_execute", registrar)

    assert respuesta.status_code == 401
    assert sentencias != [], "el mutante no tocó la base: este escenario no probaría nada (L-019)"


def test_excepciones_con_token_exactas(app_real: FastAPI) -> None:
    from ._barrido_de_rutas import rutas_efectivas

    reales = {
        (r.path, m)
        for r in rutas_efectivas(app_real)
        for m in r.methods
        if _depende_de(app_real, r.path, m, token_de_sesion_actual)
        and not _depende_de(app_real, r.path, m, identidad_actual)
    }
    assert reales == _RUTAS_CON_TOKEN
    assert _RUTAS_PUBLICAS == {("/api/salud", "GET")}


@pytest.mark.parametrize("ruta_y_metodo", sorted(_RUTAS_CUBIERTAS))
@pytest.mark.parametrize("cuerpo", [b'{"token":"sobre"}', b"", b"{", b"\xff"])
@pytest.mark.parametrize("authorization", [None, "Bearer invalido"])
def test_dos_guardas_401_cero_sql_con_cualquier_cuerpo(
    cliente: TestClient,
    app_real: FastAPI,
    mundo: dict[str, Any],
    ruta_y_metodo: tuple[str, str],
    cuerpo: bytes,
    authorization: str | None,
) -> None:
    from sqlalchemy import event

    sentencias: list[str] = []

    def contar(*args: Any) -> None:
        sentencias.append(args[2])

    headers = {"Content-Type": "application/json", "X-Proptech-Administracion": "no-uuid"}
    if authorization:
        headers["Authorization"] = authorization
    ruta, metodo = ruta_y_metodo
    event.listen(app_real.state.engine, "before_cursor_execute", contar)
    try:
        r = cliente.request(metodo, ruta.format(**mundo), content=cuerpo, headers=headers)
    finally:
        event.remove(app_real.state.engine, "before_cursor_execute", contar)
    assert r.status_code == 401, (metodo, ruta, r.text)
    assert r.json() == {"detail": "Unauthorized"}
    assert sentencias == []
