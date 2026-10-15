"""V2-1 (vuelta 3 del rompedor/auditor): el cinturón de R7
(`registrar_reset_del_tenant_al_devolver`) no puede agravar un corte de
conexión a mitad de pedido o de tarea.

Antes de esta corrección: `_checkin` hacía `dbapi_connection.cursor()` sin
mirar si es `None` (SQLAlchemy lo deja así cuando la conexión ya quedó
invalidada por el corte) — `AttributeError` dentro del evento `checkin`
aborta el "devolver al pool" de SQLAlchemy a mitad de camino, y el lugar
queda `checked out` para siempre. En la API, eso tapa el `OperationalError`
real; en el worker, `AttributeError` no es un error pasajero
(`_ERRORES_PASAJEROS_POR_NATURALEZA`) y la tarea falla sin reintento.

Contenedor propio (L-006), con el evento REAL cableado (nunca un mock, L-017:
el ataque es `pg_terminate_backend` desde una conexión de superusuario
aparte, el mismo mecanismo que usó el rompedor).

Escenarios: `cola-de-trabajos`, Base caída durante el trabajo;
`entorno-de-ejecucion`, La base se congela con una conexión abierta.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import arq
import pytest
import sqlalchemy.exc
from sqlalchemy import create_engine, text
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.reintentos import PoliticaReintentos, reintentable
from proptech_core.compartido.tenant_de_tarea import con_administracion_de_tarea

pytestmark = [pytest.mark.integracion, pytest.mark.anyio]

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RAIZ = RAIZ_BACKEND.parent

ARRANQUE_USER = "arranque_corte"
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
    # Sólo antes + upgrade head: este archivo no toca auditoria, con
    # `complejo` alcanza para tener algo que consultar.
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    try:
        yield
    finally:
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


def _engine_de_app_pool_1(contenedor: PostgresContainer) -> Any:
    """Pool de 1 conexión y overflow 0 (L-017, el mismo armado que usó el
    rompedor): así un solo corte agota el pool si el `checkin` no se
    recupera, en vez de necesitar 11 cortes con el overflow por defecto."""
    import os

    os.environ["POSTGRES_HOST"] = contenedor.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(contenedor.get_exposed_port(5432))
    os.environ["POSTGRES_APP_USER"] = APP_USER
    os.environ["POSTGRES_APP_PASSWORD"] = APP_PASSWORD
    os.environ["POSTGRES_DB"] = contenedor.dbname
    os.environ["DB_POOL_SIZE"] = "1"
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("REDIS_PASSWORD", "no-se-usa-en-este-test")
    os.environ.setdefault("PROPTECH_PARAMETROS", str(RAIZ / "config" / "parametros.yaml"))

    engine = crear_engine(Configuracion())
    engine.pool._max_overflow = 0  # type: ignore[attr-defined]
    return engine


def _engine_de_arranque(contenedor: PostgresContainer) -> Any:
    return create_engine(
        f"postgresql+psycopg://{ARRANQUE_USER}:{ARRANQUE_PASSWORD}@"
        f"{contenedor.get_container_host_ip()}:{contenedor.get_exposed_port(5432)}/"
        f"{contenedor.dbname}",
        isolation_level="AUTOCOMMIT",
    )


# --- Un corte a mitad de consulta: OperationalError, pool libre, responde la siguiente ---


async def test_un_corte_a_mitad_de_consulta_da_operationalerror_y_libera_el_pool(
    contenedor: PostgresContainer, esquema: None
) -> None:
    engine = _engine_de_app_pool_1(contenedor)
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    registrar_reset_del_tenant_al_devolver(engine)
    admin_engine = _engine_de_arranque(contenedor)
    try:
        administracion_id = uuid.uuid4()
        sesion = abrir_sesion(fabrica, administracion_id)
        pid = sesion.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with admin_engine.connect() as admin:
            admin.execute(text("SELECT pg_terminate_backend(:p)"), {"p": pid})

        with pytest.raises(sqlalchemy.exc.OperationalError):
            sesion.execute(text("SELECT count(*) FROM complejo"))
        # No tiene que levantar NADA (ni un AttributeError escondido
        # adentro del evento `checkin`, V2-1): es la prueba decisiva.
        sesion.close()

        assert engine.pool.checkedout() == 0

        sesion_siguiente = abrir_sesion(fabrica, None)
        try:
            assert sesion_siguiente.execute(text("SELECT count(*) FROM complejo")).scalar_one() == 0
        finally:
            sesion_siguiente.close()
    finally:
        engine.dispose()
        admin_engine.dispose()


# --- Lo mismo, dentro de una tarea del worker: tiene que reintentarse como pasajero ---


async def test_la_tarea_se_reintenta_como_pasajero_si_el_corte_pasa_durante_la_consulta(
    contenedor: PostgresContainer, esquema: None
) -> None:
    engine = _engine_de_app_pool_1(contenedor)
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    registrar_reset_del_tenant_al_devolver(engine)
    admin_engine = _engine_de_arranque(contenedor)

    ctx: dict[str, Any] = {
        "job_try": 1,
        "job_name": "tarea_lenta_de_prueba",
        "fabrica_de_sesiones": fabrica,
        "politica": PoliticaReintentos(espera_base=0.01, intentos_maximos=3),
    }

    @con_administracion_de_tarea
    @reintentable
    async def tarea_lenta(ctx: dict[str, Any], *, administracion_id: Any) -> tuple[Any, ...]:
        def consulta_lenta() -> tuple[Any, ...]:
            sesion = abrir_sesion(ctx["fabrica_de_sesiones"], administracion_id)
            try:
                return tuple(
                    sesion.execute(text("SELECT pg_sleep(2), count(*) FROM complejo")).one()
                )
            finally:
                sesion.close()

        return await asyncio.to_thread(consulta_lenta)

    def cortar() -> None:
        time.sleep(0.5)
        with admin_engine.connect() as admin:
            admin.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE query LIKE '%pg_sleep(2)%' AND usename = :usuario"
                ),
                {"usuario": APP_USER},
            )

    hilo = threading.Thread(target=cortar)
    hilo.start()
    try:
        with pytest.raises(arq.Retry):
            await tarea_lenta(ctx, administracion_id=str(uuid.uuid4()))
    finally:
        hilo.join()
        engine.dispose()
        admin_engine.dispose()
