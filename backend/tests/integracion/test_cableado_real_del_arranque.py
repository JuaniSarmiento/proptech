"""El cableado REAL del arranque, sin parchear nada (deuda V3-5 del 2a,
traída al 2c por la respuesta (a) a P1, tarea 6.0).

Hasta esta tarea, los únicos tests que bootean `crear_app()`/`on_startup`
con un engine real parchean `registrar_reset_del_tenant_al_devolver` (R7)
y `verificar_rol_de_aplicacion_seguro` (R8) (`test_motor_unico.py`,
`test_worker_tarea_de_prueba.py`): si alguien borra esas dos llamadas de
`app.py`/`ajustes.py`, la suite completa queda en verde igual (informe de
la vuelta 3, V3-5). Este archivo arranca la API y el worker de verdad
(`TestClient` dispara el `lifespan`; `on_startup` se llama directo) y
exige el EFECTO real de las dos, nunca sólo "no levantó":

- R7: una conexión que vuelve al pool con un `SET` de sesión (sin
  `LOCAL`) pegado tiene que salir limpia la próxima vez que alguien la
  usa — eso sólo pasa si `registrar_reset_del_tenant_al_devolver` colgó
  de verdad el evento `checkin` del engine que `lifespan`/`on_startup`
  armaron.
- R8: arrancar con un rol inseguro (el de arranque, superusuario) tiene
  que ABORTAR el arranque — eso sólo pasa si `verificar_rol_de_aplicacion_
  seguro` corrió de verdad contra ESE engine.

Contenedor propio (L-006). Escenario de `entorno-de-ejecucion`: el
cableado real de R7 y R8 al arrancar.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import RolDeAplicacionInseguro

from ._edificios import devolver_tablas_protegidas

pytestmark = pytest.mark.integracion

#: Con el patrón `proptech_[a-z_]{1,40}` (D1, L-008): en el test de R8 este
#: mismo nombre se usa como `POSTGRES_APP_USER`, campo que `Configuracion`
#: valida con ese patrón (a diferencia del campo real de arranque, que no
#: lo exige porque no es un nombre que este proyecto elija).
ARRANQUE_USER = "proptech_arranque_cableado"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


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
    import subprocess

    subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    # D3 del 4a: la base queda como la deja el deploy real (`infra/compose.yaml`),
    # con `roles despues`; sin ese paso la API y el worker no arrancan, a propósito.
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        _entorno_de_roles(contenedor),
    )
    try:
        yield
    finally:
        devolver_tablas_protegidas(contenedor, contenedor.dbname, MIGRADOR_USER)
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


def _fijar_entorno_de_app(
    monkeypatch: pytest.MonkeyPatch,
    contenedor: PostgresContainer,
    tmp_path: Any,
    *,
    usuario_app: str,
    password_app: str,
) -> None:
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", usuario_app)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", password_app)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "x")
    ruta_parametros = tmp_path / "parametros.yaml"
    ruta_parametros.write_text((RAIZ_BACKEND.parent / "config" / "parametros.yaml").read_text())
    shutil.copytree(RAIZ_BACKEND.parent / "config" / "georef", tmp_path / "georef")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta_parametros))


@pytest.fixture
def app_real(
    contenedor: PostgresContainer, esquema: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Iterator[FastAPI]:
    """`crear_app()` de verdad, con el rol SEGURO (`proptech_app`). Nunca se
    parchea `registrar_reset_del_tenant_al_devolver` ni
    `verificar_rol_de_aplicacion_seguro`: el `lifespan` real corre las dos."""
    _fijar_entorno_de_app(
        monkeypatch, contenedor, tmp_path, usuario_app=APP_USER, password_app=APP_PASSWORD
    )
    from proptech_api.app import crear_app

    app = crear_app()
    with TestClient(app):  # dispara el lifespan real, sin mocks
        yield app


# --- R7: el reset al devolver la conexión, cableado por el lifespan real ---


def test_r7_la_api_real_resetea_un_set_de_sesion_al_devolver_la_conexion(
    app_real: FastAPI,
) -> None:
    """Si `registrar_reset_del_tenant_al_devolver` no corrió de verdad
    sobre `app_real.state.engine`, un `SET` de sesión (sin `LOCAL`) hecho
    a mano sobrevive al `checkin` y la próxima conexión del pool lo ve
    pegado."""
    engine = app_real.state.engine
    administracion_falsa = "20000000-0000-0000-0000-000000000099"

    with engine.connect() as conexion:
        conexion.execute(text(f"SET app.administracion_id = '{administracion_falsa}'"))
        conexion.commit()
    # `conexion.close()` (el `with` de arriba) devuelve la conexión al
    # pool: SI el evento `checkin` real está colgado, ACÁ es donde limpia.

    with engine.connect() as otra_conexion:
        valor = otra_conexion.execute(
            text("SELECT current_setting('app.administracion_id', true)")
        ).scalar()

    assert valor in (None, ""), (
        f"el SET de sesión sobrevivió al checkin (valor={valor!r}): "
        "registrar_reset_del_tenant_al_devolver no corrió de verdad sobre el engine real"
    )


# --- R8: el rechazo de un rol inseguro, cableado por el lifespan real ---


def test_r8_la_api_real_no_arranca_si_el_rol_es_inseguro(
    contenedor: PostgresContainer,
    esquema: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """`POSTGRES_APP_USER`/`PASSWORD` apuntan al rol de ARRANQUE (superusuario):
    si `verificar_rol_de_aplicacion_seguro` corre de verdad dentro del
    `lifespan`, `TestClient(app)` tiene que fallar al entrar, nombrando la
    causa. Si en cambio arranca sin levantar, la llamada no está corriendo."""
    _fijar_entorno_de_app(
        monkeypatch,
        contenedor,
        tmp_path,
        usuario_app=contenedor.username,
        password_app=contenedor.password,
    )
    from proptech_api.app import crear_app

    app = crear_app()
    with pytest.raises(RolDeAplicacionInseguro, match="superusuario"):
        with TestClient(app):
            # Si llega hasta acá, la API arrancó con el rol de arranque
            # (superusuario): verificar_rol_de_aplicacion_seguro no corrió
            # de verdad en el lifespan. `pytest.raises` de afuera va a
            # fallar con "DID NOT RAISE", que ya nombra la causa.
            pass


# --- Gemelo del worker (L-009): mismo cableado en on_startup ---


@pytest.fixture
def entorno_del_worker(
    contenedor: PostgresContainer,
    esquema: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    ajustes_del_worker: object,
) -> Any:
    """Construye una `Configuracion` propia (nunca la global `_configuracion`
    de `proptech_worker.ajustes`, que ya se fijó al importar el módulo por
    primera vez en esta sesión de pytest) para poder variar el rol entre
    los dos tests de este archivo.

    Depende de `ajustes_del_worker` (conftest) aunque no use su valor: ese
    fixture de SESIÓN es el que tiene que importar `proptech_worker.ajustes`
    por primera vez, con el entorno correcto del contenedor de sesión. Sin
    esta dependencia, si este archivo corre primero, el import ocurre
    recién acá, con el entorno de ESTE test (`REDIS_HOST=127.0.0.1`,
    `REDIS_PORT=1`), y `monkeypatch.setattr` más abajo "restaura" ese
    mismo valor roto al terminar — hallazgo real, visto corriendo la
    suite completa, no sólo este archivo (L-013/L-016 otra vez): el resto
    de los tests de worker de la sesión quedaban sin Redis.

    Sólo `monkeypatch.setenv` (nunca `os.environ.update`, que no se
    revierte solo) para el entorno de ESTE test."""
    from proptech_core.compartido.configuracion import Configuracion

    ruta_parametros = tmp_path / "parametros.yaml"
    ruta_parametros.write_text((RAIZ_BACKEND.parent / "config" / "parametros.yaml").read_text())

    def _construir(usuario_app: str, password_app: str) -> Any:
        entorno = {
            "POSTGRES_HOST": contenedor.get_container_host_ip(),
            "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
            "POSTGRES_APP_USER": usuario_app,
            "POSTGRES_APP_PASSWORD": password_app,
            "POSTGRES_DB": contenedor.dbname,
            "REDIS_HOST": "127.0.0.1",
            "REDIS_PORT": "1",
            "REDIS_PASSWORD": "x",
            "PROPTECH_PARAMETROS": str(ruta_parametros),
        }
        for clave, valor in entorno.items():
            monkeypatch.setenv(clave, valor)
        return Configuracion()

    return _construir


@pytest.mark.anyio
async def test_r7_el_worker_real_resetea_un_set_de_sesion_al_devolver_la_conexion(
    entorno_del_worker: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gemelo del test de la API (L-009): se llama `on_startup` real,
    sustituyendo sólo la `Configuracion` que usa (no R7 ni R8), para poder
    apuntar a este contenedor propio en vez del de sesión."""
    # El entorno se fija ANTES de importar: si este es el primer import de
    # `proptech_worker.ajustes` en la sesión de pytest, su `_configuracion`
    # de módulo se construye al importarlo (lee el entorno en ese momento);
    # si ya estaba importado por otro archivo, el `monkeypatch.setattr` de
    # abajo la pisa igual.
    configuracion_segura = entorno_del_worker(APP_USER, APP_PASSWORD)
    import proptech_worker.ajustes as ajustes_mod

    monkeypatch.setattr(ajustes_mod, "_configuracion", configuracion_segura)

    ctx: dict[str, Any] = {}
    await ajustes_mod.on_startup(ctx)
    engine = ctx["engine"]
    administracion_falsa = "20000000-0000-0000-0000-000000000098"
    try:
        with engine.connect() as conexion:
            conexion.execute(text(f"SET app.administracion_id = '{administracion_falsa}'"))
            conexion.commit()

        with engine.connect() as otra_conexion:
            valor = otra_conexion.execute(
                text("SELECT current_setting('app.administracion_id', true)")
            ).scalar()

        assert valor in (None, ""), (
            f"el SET de sesión sobrevivió al checkin (valor={valor!r}) en el worker: "
            "registrar_reset_del_tenant_al_devolver no corrió de verdad en on_startup"
        )
    finally:
        engine.dispose()


@pytest.mark.anyio
async def test_r8_el_worker_real_no_arranca_si_el_rol_es_inseguro(
    entorno_del_worker: Any,
    monkeypatch: pytest.MonkeyPatch,
    contenedor: PostgresContainer,
) -> None:
    """Gemelo del test de la API: `POSTGRES_APP_USER`/`PASSWORD` apuntan al
    rol de arranque (superusuario); `on_startup` real tiene que levantar
    `RolDeAplicacionInseguro`, nunca terminar "arrancado" en silencio."""
    configuracion_insegura = entorno_del_worker(contenedor.username, contenedor.password)
    import proptech_worker.ajustes as ajustes_mod

    monkeypatch.setattr(ajustes_mod, "_configuracion", configuracion_insegura)

    # `on_startup` sólo pone `ctx["engine"]` DESPUÉS de verificar el rol
    # (ver `ajustes.py`): si esto levanta de verdad, nunca llega a ponerlo,
    # así que no hay nada que haya que `dispose()`-ar acá.
    ctx: dict[str, Any] = {}
    with pytest.raises(RolDeAplicacionInseguro, match="superusuario"):
        await ajustes_mod.on_startup(ctx)
    assert "engine" not in ctx, (
        "el worker arrancó con el rol de arranque (superusuario): "
        "verificar_rol_de_aplicacion_seguro no corrió de verdad en on_startup"
    )
