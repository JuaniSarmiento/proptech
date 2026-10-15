"""`tarea_de_prueba_con_administracion` contra PostgreSQL real (D4, D8,
cambio 2a, tarea 7.1): el tenant del worker, llamada directa con un `ctx`
armado a mano (nunca a través de Redis/ARQ: esta tarea no se registra en
`AjustesDelWorker`, y no hace falta para probar D4/D8 sobre ella).

Contenedor propio (L-006): igual que 4.1/4.2, nunca el compartido de sesión
— `administracion`/`complejo` son tablas de la 3.1, y un ciclo de
`upgrade`/`downgrade` de otro archivo sobre el contenedor compartido las
deja sin existir a mitad de sesión (el mismo hallazgo de la 4.1).

Tampoco se reutiliza `proptech_worker.ajustes` (que fija su `Configuracion`
una sola vez, al importarse, apuntando al contenedor que esté en el
entorno en ese momento): el `ctx` de este archivo arma su propio engine
contra SU contenedor, con `crear_engine`/`registrar_tenant_por_administracion`
directo (D4).

Escenarios de `cola-de-trabajos`: Dos tareas seguidas; El tenant llega al
hilo. Lecciones: L-006, L-009, L-015.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.configuracion import Configuracion
from proptech_worker.prueba import tarea_de_prueba_con_administracion

pytestmark = [pytest.mark.integracion, pytest.mark.anyio]

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RAIZ = RAIZ_BACKEND.parent

ARRANQUE_USER = "arranque_worker_tenant"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


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


def _sembrar_administracion_con_complejos(
    contenedor: PostgresContainer, cantidad: int
) -> uuid.UUID:
    administracion_id = uuid.uuid4()
    conexion = psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
        dbname=contenedor.dbname,
        autocommit=True,
    )
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)",
                (str(administracion_id),),
            )
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                (str(administracion_id), "Administración de la tarea 7.1"),
            )
            for índice in range(cantidad):
                cur.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                    (str(uuid.uuid4()), str(administracion_id), f"Complejo {índice}"),
                )
    finally:
        conexion.close()
    return administracion_id


def _ctx(contenedor: PostgresContainer) -> dict[str, Any]:
    """Arma un `ctx` de worker mínimo (D2, D4), sin Redis ni ARQ: conecta
    como `proptech_app` contra ESTE contenedor, nunca el de
    `proptech_worker.ajustes` (que ya fijó su `Configuracion` contra el
    contenedor compartido al importarse)."""
    import os

    os.environ["POSTGRES_HOST"] = contenedor.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(contenedor.get_exposed_port(5432))
    os.environ["POSTGRES_APP_USER"] = APP_USER
    os.environ["POSTGRES_APP_PASSWORD"] = APP_PASSWORD
    os.environ["POSTGRES_DB"] = contenedor.dbname
    # Nunca se usan de verdad (esta tarea no toca Redis): sólo tienen que
    # pasar la validación de `Configuracion`.
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("REDIS_PASSWORD", "no-se-usa-en-este-test")
    os.environ.setdefault("PROPTECH_PARAMETROS", str(RAIZ / "config" / "parametros.yaml"))

    configuracion = Configuracion()
    engine = crear_engine(configuracion)
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    return {
        "job_try": 1,
        "job_name": "tarea_de_prueba_con_administracion",
        "fabrica_de_sesiones": fabrica,
        "engine": engine,
    }


async def test_cuenta_solo_los_complejos_de_su_administracion(
    contenedor: PostgresContainer, esquema: None
) -> None:
    administracion_id = _sembrar_administracion_con_complejos(contenedor, 3)
    ctx = _ctx(contenedor)
    try:
        cantidad = await tarea_de_prueba_con_administracion(
            ctx, request_id=str(uuid.uuid4()), administracion_id=str(administracion_id)
        )
    finally:
        ctx["engine"].dispose()
    assert cantidad == 3


async def test_dos_tareas_seguidas_ven_cada_una_lo_suyo(
    contenedor: PostgresContainer, esquema: None
) -> None:
    administracion_a = _sembrar_administracion_con_complejos(contenedor, 2)
    administracion_b = _sembrar_administracion_con_complejos(contenedor, 5)
    ctx = _ctx(contenedor)
    try:
        cantidad_a = await tarea_de_prueba_con_administracion(
            ctx, request_id=str(uuid.uuid4()), administracion_id=str(administracion_a)
        )
        cantidad_b = await tarea_de_prueba_con_administracion(
            ctx, request_id=str(uuid.uuid4()), administracion_id=str(administracion_b)
        )
        # Y de nuevo A, para probar que B no le dejó nada pegado (D8: "no
        # hay estado ambiente que pase a la tarea siguiente").
        cantidad_a_otra_vez = await tarea_de_prueba_con_administracion(
            ctx, request_id=str(uuid.uuid4()), administracion_id=str(administracion_a)
        )
    finally:
        ctx["engine"].dispose()
    assert cantidad_a == 2
    assert cantidad_b == 5
    assert cantidad_a_otra_vez == 2


async def test_el_tenant_llega_al_hilo_de_asyncio_to_thread(
    contenedor: PostgresContainer, esquema: None
) -> None:
    """La tarea misma ya corre su cuenta con `asyncio.to_thread` (L-015):
    tres llamadas concurrentes al mismo tenant, en hilos distintos, tienen
    que ver todas el mismo conteo — si el tenant dependiera del hilo en vez
    de viajar en `session.info`, alguna vería 0."""
    administracion_id = _sembrar_administracion_con_complejos(contenedor, 7)
    ctx = _ctx(contenedor)
    try:
        resultados = await asyncio.gather(
            *(
                tarea_de_prueba_con_administracion(
                    ctx, request_id=str(uuid.uuid4()), administracion_id=str(administracion_id)
                )
                for _ in range(3)
            )
        )
    finally:
        ctx["engine"].dispose()
    assert resultados == [7, 7, 7]
