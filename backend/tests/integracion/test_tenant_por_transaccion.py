"""`abrir_sesion` y el `after_begin` del tenant por transacción (D4, cambio
2a, tarea 4.1), contra PostgreSQL real, conectados como `proptech_app`.

Usa el contenedor de sesión (`postgres_contenedor`) con los roles reales y
el esquema migrado (`roles_reales`, `esquema_migrado`, `tests/conftest.py`):
este archivo no muta roles ni esquema, sólo lee y escribe por sesiones de
SQLAlchemy, así que no hace falta un contenedor propio (a diferencia de
3.1/3.2, que sí tocaban roles y catálogo).

Escenarios de `aislamiento-por-administracion`: El pedido siguiente no
hereda; Una segunda transacción en el mismo pedido. Lecciones: L-009, L-015.
"""

import asyncio
import threading
import uuid
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.configuracion import Configuracion

pytestmark = pytest.mark.integracion


def _conectar_como_migrador(
    contenedor: PostgresContainer, usuario: str, password: str
) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario,
        password=password,
        dbname=contenedor.dbname,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def dos_administraciones_con_complejo(
    postgres_contenedor: PostgresContainer, roles_reales: None, esquema_migrado: None
) -> dict[str, Any]:
    from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION

    conexion = _conectar_como_migrador(
        postgres_contenedor, MIGRADOR_USER_DE_SESION, MIGRADOR_PASSWORD_DE_SESION
    )
    datos: dict[str, Any] = {}
    with conexion.cursor() as cur:
        for clave in ("a", "b"):
            admin_id = uuid.uuid4()
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                (str(admin_id), f"Tenant {clave.upper()}"),
            )
            complejo_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                (str(complejo_id), str(admin_id), f"Complejo {clave.upper()}"),
            )
            datos[clave] = {"administracion_id": admin_id, "complejo_id": complejo_id}
    conexion.close()
    return datos


@pytest.fixture
def fabrica_pool_1(
    postgres_contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sessionmaker[Session]]:
    """Engine con `pool_size=1` (la tarea lo pide explícito): la prueba más
    estricta de que `set_config(..., true)` no sobrevive al devolver la
    conexión al pool es reusar la MISMA conexión física entre sesiones."""
    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    monkeypatch.setenv("POSTGRES_HOST", postgres_contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(postgres_contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("POSTGRES_DB", postgres_contenedor.dbname)
    monkeypatch.setenv("DB_POOL_SIZE", "1")

    engine = crear_engine(Configuracion())
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    try:
        yield fabrica
    finally:
        engine.dispose()


def _complejos_visibles(sesion: Session) -> list[str]:
    filas = sesion.execute(text("SELECT nombre FROM complejo ORDER BY nombre")).fetchall()
    return [fila[0] for fila in filas]


# --- El pedido siguiente no hereda el tenant (D4, D8) ---


def test_sesion_con_tenant_commit_y_siguiente_sin_tenant_no_hereda(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion_1 = abrir_sesion(fabrica_pool_1, admin_a)
    assert _complejos_visibles(sesion_1) == ["Complejo A"]
    sesion_1.commit()
    sesion_1.close()

    # Misma fábrica, mismo pool de tamaño 1: si el engine tuviera más de una
    # conexión esto no probaría nada (podría tocarle otra conexión limpia).
    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    assert _complejos_visibles(sesion_2) == []
    sesion_2.close()


def test_sesion_con_tenant_rollback_y_siguiente_sin_tenant_no_hereda(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion_1 = abrir_sesion(fabrica_pool_1, admin_a)
    assert _complejos_visibles(sesion_1) == ["Complejo A"]
    sesion_1.rollback()
    sesion_1.close()

    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    assert _complejos_visibles(sesion_2) == []
    sesion_2.close()


def test_sesion_con_tenant_tras_excepcion_y_siguiente_sin_tenant_no_hereda(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion_1 = abrir_sesion(fabrica_pool_1, admin_a)
    assert _complejos_visibles(sesion_1) == ["Complejo A"]
    with pytest.raises(Exception):  # noqa: B017 (cualquier error de la base alcanza)
        sesion_1.execute(text("SELECT 1 / 0"))
    sesion_1.rollback()  # una sesión con una transacción abortada exige esto
    sesion_1.close()

    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    assert _complejos_visibles(sesion_2) == []
    sesion_2.close()


# --- Una segunda transacción en el mismo pedido sigue viendo A (D4) ---


def test_commit_a_mitad_de_sesion_la_transaccion_siguiente_sigue_viendo_a(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion = abrir_sesion(fabrica_pool_1, admin_a)
    try:
        assert _complejos_visibles(sesion) == ["Complejo A"]
        sesion.commit()  # cierra la primera transacción, DENTRO de la misma sesión
        assert _complejos_visibles(sesion) == ["Complejo A"]  # la segunda, mismo tenant
    finally:
        sesion.close()


# --- Sin `abrir_sesion`: cero filas, nunca un error ---


def test_sesion_abierta_directo_con_la_fabrica_lee_cero_filas(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    sesion = fabrica_pool_1()
    try:
        assert _complejos_visibles(sesion) == []
    finally:
        sesion.close()


# --- Un tenant que no es UUID levanta antes de tocar la base ---


def test_tenant_que_no_es_uuid_levanta_antes_de_ejecutar_sql(
    fabrica_pool_1: sessionmaker[Session],
) -> None:
    sesion = fabrica_pool_1(info={"administracion_id": "no-es-un-uuid"})
    try:
        with pytest.raises(TypeError):
            sesion.execute(text("SELECT 1"))
    finally:
        sesion.rollback()
        sesion.close()


# --- El tenant no depende del hilo que ejecuta el SQL (L-015) ---


def _bateria_en_este_hilo(fabrica: sessionmaker[Session], admin_a: uuid.UUID) -> list[str]:
    sesion = abrir_sesion(fabrica, admin_a)
    try:
        return _complejos_visibles(sesion)
    finally:
        sesion.close()


def test_la_bateria_ve_a_desde_un_threading_thread(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]
    resultado: list[list[str]] = []

    hilo = threading.Thread(
        target=lambda: resultado.append(_bateria_en_este_hilo(fabrica_pool_1, admin_a))
    )
    hilo.start()
    hilo.join()

    assert resultado == [["Complejo A"]]


@pytest.mark.anyio
async def test_la_bateria_ve_a_desde_asyncio_to_thread(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    resultado = await asyncio.to_thread(_bateria_en_este_hilo, fabrica_pool_1, admin_a)

    assert resultado == ["Complejo A"]
