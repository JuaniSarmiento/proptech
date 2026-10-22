"""`abrir_sesion` y el `after_begin` del tenant por transacción (D4, cambio
2a, tarea 4.1), contra PostgreSQL real, conectados como `proptech_app`.

Contenedor propio (L-006), nunca el de sesión: varios archivos de
integración ya existentes (`test_idempotencia.py`, `test_migracion_
trabajos_hechos.py`, `test_migraciones_y_salud_real.py`) corren su propio
ciclo completo `upgrade head` / `downgrade base` sobre el contenedor de
sesión, confiando en que corren ANTES de que algo dispare `esquema_migrado`
por primera vez (ese fixture es de sesión: una vez que corre, no se repite).
Este archivo y `test_identidad_api.py` disparaban `esquema_migrado` antes
en el orden alfabético que esos otros archivos, así que el `downgrade base`
de ellos corría DESPUÉS y le borraba el esquema a este archivo a mitad de
sesión (`UndefinedTable: relation "administracion" does not exist`, visto
corriendo la suite completa). Un contenedor propio evita depender de ese
orden.

Escenarios de `aislamiento-por-administracion`: El pedido siguiente no
hereda; Una segunda transacción en el mismo pedido. Lecciones: L-009, L-015.
"""

import asyncio
import subprocess
import sys
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.configuracion import Configuracion

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_tenant"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


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
def dos_administraciones_con_complejo(
    contenedor: PostgresContainer, esquema: None
) -> dict[str, Any]:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
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
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, %s, 'Mendoza')",
                (str(complejo_id), str(admin_id), f"Complejo {clave.upper()}"),
            )
            datos[clave] = {"administracion_id": admin_id, "complejo_id": complejo_id}
    conexion.close()
    return datos


@pytest.fixture
def fabrica_pool_1(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sessionmaker[Session]]:
    """Engine con `pool_size=1` (la tarea lo pide explícito): la prueba más
    estricta de que `set_config(..., true)` no sobrevive al devolver la
    conexión al pool es reusar la MISMA conexión física entre sesiones."""
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("DB_POOL_SIZE", "1")

    engine = crear_engine(Configuracion())
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    # R7 (vuelta 2): el cinturón de más, sobre el MISMO engine que usan los
    # tests de este archivo — así el rojo/verde de R7 es comparable con el
    # resto (mismo pool de 1 conexión).
    registrar_reset_del_tenant_al_devolver(engine)
    try:
        yield fabrica
    finally:
        engine.dispose()


@pytest.fixture
def motor_y_fabrica_pool_1(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    """Gemelo de `fabrica_pool_1`, pero expone también el `Engine`: N-c (D-02,
    `12_fichas_de_changes.md:959`) necesita abrir una `Connection` propia con
    `engine.connect()` y mantenerla fuera del pool entre dos transacciones,
    para que ninguna de las dos pase por `checkin` — el cinturón de R7
    resetea `app.administracion_id` justo ahí y tapa si el `SET` de D4 es
    realmente local a la transacción o quedó de sesión."""
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("DB_POOL_SIZE", "1")

    engine = crear_engine(Configuracion())
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    registrar_reset_del_tenant_al_devolver(engine)
    try:
        yield engine, fabrica
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

    # Deuda V3-9 (2a), tarea 4.2: `sesion_1.close()` suelto (sin `finally`)
    # no corre si el `assert` de arriba falla, y sobre un pool de 1 conexión
    # eso cuelga `abrir_sesion` de `sesion_2` esperando una conexión que
    # nunca se devuelve (el cuelgue que V3-9 nombra).
    sesion_1 = abrir_sesion(fabrica_pool_1, admin_a)
    try:
        assert _complejos_visibles(sesion_1) == ["Complejo A"]
        sesion_1.commit()
    finally:
        sesion_1.close()

    # Misma fábrica, mismo pool de tamaño 1: si el engine tuviera más de una
    # conexión esto no probaría nada (podría tocarle otra conexión limpia).
    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    try:
        assert _complejos_visibles(sesion_2) == []
    finally:
        sesion_2.close()


def test_sesion_con_tenant_rollback_y_siguiente_sin_tenant_no_hereda(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion_1 = abrir_sesion(fabrica_pool_1, admin_a)
    try:
        assert _complejos_visibles(sesion_1) == ["Complejo A"]
        sesion_1.rollback()
    finally:
        sesion_1.close()

    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    try:
        assert _complejos_visibles(sesion_2) == []
    finally:
        sesion_2.close()


def test_sesion_con_tenant_tras_excepcion_y_siguiente_sin_tenant_no_hereda(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion_1 = abrir_sesion(fabrica_pool_1, admin_a)
    try:
        assert _complejos_visibles(sesion_1) == ["Complejo A"]
        with pytest.raises(Exception):  # noqa: B017 (cualquier error de la base alcanza)
            sesion_1.execute(text("SELECT 1 / 0"))
        sesion_1.rollback()  # una sesión con una transacción abortada exige esto
    finally:
        sesion_1.close()

    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    try:
        assert _complejos_visibles(sesion_2) == []
    finally:
        sesion_2.close()


# --- Vuelta 2, R7: un SET de sesión (sin LOCAL) no contagia al pedido siguiente ---


def test_un_set_de_sesion_sin_local_no_contagia_gracias_al_reset_de_checkin(
    fabrica_pool_1: sessionmaker[Session], dos_administraciones_con_complejo: dict[str, Any]
) -> None:
    """El ataque real (informe del rompedor, vuelta 1, R7): un `SET` de
    sesión (sin `LOCAL`) del tenant — nunca lo hace `abrir_sesion`/
    `registrar_tenant_por_administracion`, que siempre usan
    `set_config(..., true)`, pero sí lo haría un código futuro equivocado.
    Ese `SET` sobrevive al `ROLLBACK` que el pool ya hace al devolver la
    conexión, porque un `SET` de sesión no es parte de la transacción que
    se revierte. `registrar_reset_del_tenant_al_devolver` es el cinturón:
    sin él, la sesión siguiente sin tenant ve las 2 filas de A."""
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    sesion_1 = abrir_sesion(fabrica_pool_1, None)
    try:
        # Un SET de sesión directo, simulando el error: nunca pasa por
        # abrir_sesion ni por el evento after_begin.
        sesion_1.execute(text(f"SET app.administracion_id = '{admin_a}'"))
        assert _complejos_visibles(sesion_1) == ["Complejo A"]
        sesion_1.commit()
    finally:
        sesion_1.close()

    sesion_2 = abrir_sesion(fabrica_pool_1, None)
    try:
        assert _complejos_visibles(sesion_2) == []
    finally:
        sesion_2.close()


# --- N-c (D-02): el SET de D4 es local a la transacción, no de sesión ---


def test_set_config_de_administracion_id_no_sobrevive_al_commit_sin_pasar_por_checkin(
    motor_y_fabrica_pool_1: tuple[Engine, sessionmaker[Session]],
    dos_administraciones_con_complejo: dict[str, Any],
) -> None:
    """N-c (deuda D-02, `12_fichas_de_changes.md:959`): hasta este test, nada
    daba rojo si `set_config('app.administracion_id', ..., true)` (D4,
    `after_begin`) se cambiara por `set_config(..., false)` — un `SET` de
    sesión en vez de uno local a la transacción. Los tests de "no hereda" de
    arriba no lo detectan: cada `commit` de una `Session` del ORM devuelve la
    conexión al pool (`checkin`) y la vuelve a sacar (`checkout`) para la
    transacción siguiente, así que el cinturón de R7
    (`registrar_reset_del_tenant_al_devolver`) resetea `app.administracion_id`
    en CADA commit, se haya fijado con `true` o con `false`. El resultado es
    el mismo en los dos casos y el mutante queda tapado.

    Por eso las dos sesiones de este test comparten la MISMA `Connection`,
    abierta a mano con `engine.connect()` y nunca devuelta al pool entre una
    sesión y la otra (`sesion.close()` sobre una sesión ligada a una
    `Connection` externa no dispara `checkin`, sólo `conexion.close()` lo
    hace, al final). Si el `SET` de la primera transacción fuera de sesión
    (mutante `false`), nada lo limpia entre medio y la segunda sesión — sin
    tenant — vería las filas de A.
    """
    engine, fabrica = motor_y_fabrica_pool_1
    admin_a = dos_administraciones_con_complejo["a"]["administracion_id"]

    conexion = engine.connect()
    try:
        sesion_1 = fabrica(bind=conexion, info={"administracion_id": admin_a})
        try:
            assert _complejos_visibles(sesion_1) == ["Complejo A"]
            sesion_1.commit()
        finally:
            sesion_1.close()

        # Misma `conexion` que arriba, todavía sin pasar por el pool: si
        # `set_config` fue realmente local a la transacción (D4), acá no
        # queda nada fijado y la política de RLS (D5) da cero filas.
        sesion_2 = fabrica(bind=conexion, info={"administracion_id": None})
        try:
            assert _complejos_visibles(sesion_2) == []
        finally:
            sesion_2.close()
    finally:
        conexion.close()


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
