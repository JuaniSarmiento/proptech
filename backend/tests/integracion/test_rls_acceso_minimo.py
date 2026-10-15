"""Migración `0003_acceso_minimo`: RLS forzada y la política de D5 contra
PostgreSQL real (D5, D6, cambio 2a, tarea 3.1).

Contenedor propio (L-006, nunca el de sesión): esta migración todavía no
existe para el resto de la suite, y el ciclo completo de `upgrade`/`downgrade`
no debería dejarle estado a nadie más. Todos los tests que leen o escriben
datos de administración se conectan como `proptech_app` (L-016: un test que
conecta como superusuario pasa siempre, sin probar nada); sembrar datos de
las dos administraciones de prueba se hace como `proptech_migrador` (E1: no
tiene `BYPASSRLS`, así que la migración que siembra datos también tiene que
fijar su tenant a propósito, con su propio `set_config`).

Escenarios de `aislamiento-por-administracion`: Otra administración no ve
nada; Escritura cruzada rechazada; Referencia cruzada rechazada; Referencia a
otro edificio rechazada; Tenant ausente; Tenant vacío. Lecciones: L-016, L-017.
"""

import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_rls"
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
    entorno = {
        **_entorno_de_roles(contenedor),
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD,
    }
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _correr(args: list[str], entorno: dict[str, str]) -> None:
    subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    """Roles reales + `upgrade head` (0003) una sola vez por módulo; al
    final, `downgrade` a `base` para no dejarle estado a nadie (L-006)."""
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    try:
        yield
    finally:
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


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
def dos_administraciones(contenedor: PostgresContainer, esquema: None) -> dict[str, Any]:
    """Siembra A y B como `proptech_migrador`, fijando su propio tenant con
    `set_config` antes de cada INSERT (E1): el migrador no tiene `BYPASSRLS`,
    así que la política también lo alcanza. Devuelve ids reales (UUID
    existentes, L-017) para los tests."""
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    datos: dict[str, Any] = {}
    with conexion.cursor() as cur:
        for clave in ("a", "b"):
            admin_id = uuid.uuid4()
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, %s)",
                (str(admin_id), f"Administración {clave.upper()}"),
            )
            complejo_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                (str(complejo_id), str(admin_id), f"Complejo {clave.upper()}"),
            )
            unidad_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO unidad (id, administracion_id, complejo_id, nombre) "
                "VALUES (%s, %s, %s, %s)",
                (str(unidad_id), str(admin_id), str(complejo_id), f"1A-{clave}"),
            )
            persona_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s, %s, %s, %s)",
                (str(persona_id), str(admin_id), f"Persona {clave}", f"persona-{clave}@ej.com"),
            )
            datos[clave] = {
                "administracion_id": admin_id,
                "complejo_id": complejo_id,
                "unidad_id": unidad_id,
                "persona_id": persona_id,
            }
    conexion.close()
    return datos


def _sesion_app(
    contenedor: PostgresContainer, tenant: uuid.UUID | str | None
) -> psycopg.Connection:
    """Conexión como `proptech_app` con el tenant fijado por `SET LOCAL` en
    una transacción (equivalente a `set_config(..., true)`, D4). `tenant=None`
    no fija nada (tenant ausente); `tenant=""` fija la cadena vacía (tenant
    vacío)."""
    conexion = _conectar(contenedor, APP_USER, APP_PASSWORD)
    conexion.autocommit = False
    if tenant is not None:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(tenant),))
    return conexion


# --- Tenant ausente y tenant vacío: cero filas, nunca un error (D5) ---


@pytest.mark.parametrize("tenant", [None, ""], ids=["ausente", "vacio"])
@pytest.mark.parametrize(
    "tabla", ["administracion", "complejo", "unidad", "persona", "asignacion_rol"]
)
def test_sin_tenant_cero_filas_y_sin_error(
    contenedor: PostgresContainer,
    dos_administraciones: dict[str, Any],
    tabla: str,
    tenant: str | None,
) -> None:
    conexion = _sesion_app(contenedor, tenant)
    try:
        with conexion.cursor() as cur:
            cur.execute(f"SELECT * FROM {tabla}")  # noqa: S608 (tabla de una lista fija)
            assert cur.fetchall() == []
    finally:
        conexion.close()


# --- Otra administración no ve nada ---


def test_el_complejo_de_otra_administracion_da_cero_filas(
    contenedor: PostgresContainer, dos_administraciones: dict[str, Any]
) -> None:
    conexion = _sesion_app(contenedor, dos_administraciones["a"]["administracion_id"])
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT * FROM complejo WHERE id = %s",
                (str(dos_administraciones["b"]["complejo_id"]),),
            )
            assert cur.fetchall() == []
    finally:
        conexion.close()


# --- Escritura cruzada rechazada ---


@pytest.mark.parametrize("operacion", ["insert", "update"])
def test_escritura_cruzada_falla_y_no_deja_nada(
    contenedor: PostgresContainer, dos_administraciones: dict[str, Any], operacion: str
) -> None:
    conexion = _sesion_app(contenedor, dos_administraciones["a"]["administracion_id"])
    try:
        with conexion.cursor() as cur:
            if operacion == "insert":
                # No es un CHECK: es la política WITH CHECK de RLS (D5), que
                # Postgres reporta como "insufficient privilege".
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute(
                        "INSERT INTO complejo (administracion_id, nombre) VALUES (%s, %s)",
                        (str(dos_administraciones["b"]["administracion_id"]), "intruso"),
                    )
            else:
                cur.execute(
                    "UPDATE complejo SET nombre = 'hackeado' WHERE id = %s",
                    (str(dos_administraciones["b"]["complejo_id"]),),
                )
                assert cur.rowcount == 0
        conexion.rollback()
    finally:
        conexion.close()

    # Nada cambió: verificado como el migrador, fijando el tenant de B.
    verificacion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    with verificacion.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.administracion_id', %s, false)",
            (str(dos_administraciones["b"]["administracion_id"]),),
        )
        cur.execute(
            "SELECT nombre FROM complejo WHERE id = %s",
            (str(dos_administraciones["b"]["complejo_id"]),),
        )
        assert cur.fetchone() == ("Complejo B",)
    verificacion.close()


# --- Referencia a otro edificio / cruzada rechazada (FK compuesta) ---


def test_unidad_colgada_de_un_complejo_de_otra_administracion_falla_por_fk(
    contenedor: PostgresContainer, dos_administraciones: dict[str, Any]
) -> None:
    """Una fila de A que apunta al complejo de B: la FK compuesta
    `(administracion_id, complejo_id)` no encuentra ese par en `complejo`."""
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)",
                (str(dos_administraciones["a"]["administracion_id"]),),
            )
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                cur.execute(
                    "INSERT INTO unidad (administracion_id, complejo_id, nombre) "
                    "VALUES (%s, %s, %s)",
                    (
                        str(dos_administraciones["a"]["administracion_id"]),
                        str(dos_administraciones["b"]["complejo_id"]),
                        "intrusa",
                    ),
                )
    finally:
        conexion.rollback()
        conexion.close()


def test_asignacion_con_unidad_de_otro_complejo_de_la_misma_administracion_falla_por_fk(
    contenedor: PostgresContainer, dos_administraciones: dict[str, Any]
) -> None:
    """La FK `(administracion_id, complejo_id, unidad_id)` exige que la
    unidad sea DE ESE complejo, no sólo de la misma administración."""
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    admin_a = dos_administraciones["a"]["administracion_id"]
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_a),))
            otro_complejo_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre) VALUES (%s, %s, %s)",
                (str(otro_complejo_id), str(admin_a), "Otro complejo de A"),
            )
            persona_id = dos_administraciones["a"]["persona_id"]
            unidad_del_otro_complejo = dos_administraciones["a"]["unidad_id"]
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                cur.execute(
                    "INSERT INTO asignacion_rol "
                    "(administracion_id, persona_id, rol, complejo_id, unidad_id) "
                    "VALUES (%s, %s, 'vecino', %s, %s)",
                    (
                        str(admin_a),
                        str(persona_id),
                        str(otro_complejo_id),
                        str(unidad_del_otro_complejo),
                    ),
                )
    finally:
        conexion.rollback()
        conexion.close()


# --- CHECK por rol: vecino sin unidad, colaborador sin nivel ---


@pytest.mark.parametrize(
    "columnas_extra",
    [
        {"rol": "vecino", "sin": "unidad_id"},
        {"rol": "colaborador", "sin": "nivel"},
    ],
    ids=["vecino_sin_unidad", "colaborador_sin_nivel"],
)
def test_asignacion_incompleta_para_su_rol_falla_por_check(
    contenedor: PostgresContainer,
    dos_administraciones: dict[str, Any],
    columnas_extra: dict[str, str],
) -> None:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    admin_a = dos_administraciones["a"]["administracion_id"]
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_a),))
            rol = columnas_extra["rol"]
            if rol == "vecino":
                sql = (
                    "INSERT INTO asignacion_rol "
                    "(administracion_id, persona_id, rol, complejo_id) VALUES (%s, %s, %s, %s)"
                )
                parametros = (
                    str(admin_a),
                    str(dos_administraciones["a"]["persona_id"]),
                    rol,
                    str(dos_administraciones["a"]["complejo_id"]),
                )
            else:
                sql = (
                    "INSERT INTO asignacion_rol "
                    "(administracion_id, persona_id, rol, complejo_id) VALUES (%s, %s, %s, %s)"
                )
                parametros = (
                    str(admin_a),
                    str(dos_administraciones["a"]["persona_id"]),
                    rol,
                    str(dos_administraciones["a"]["complejo_id"]),
                )
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(sql, parametros)
    finally:
        conexion.rollback()
        conexion.close()


# --- Email único por administración, no global ---


def test_mismo_email_en_la_misma_administracion_falla_y_entre_administraciones_pasa(
    contenedor: PostgresContainer, dos_administraciones: dict[str, Any]
) -> None:
    admin_a = dos_administraciones["a"]["administracion_id"]
    admin_b = dos_administraciones["b"]["administracion_id"]
    email_repetido = "repetido-unico-de-este-test@ej.com"

    # 1) Falla dentro de la misma administración: transacción propia, con
    # autocommit en False para que el rollback deshaga también la primera
    # fila (si no, "Primera" ya habría quedado confirmada antes del rollback).
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    conexion.autocommit = False
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_a),))
            cur.execute(
                "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
                (str(admin_a), "Primera", email_repetido),
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
                    (str(admin_a), "Segunda, misma administración", email_repetido),
                )
    finally:
        conexion.rollback()
        conexion.close()

    # 2) Pasa entre administraciones distintas: conexión nueva, para que no
    # quede ninguna duda de que lo anterior se deshizo de verdad.
    conexion2 = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    conexion2.autocommit = False
    try:
        with conexion2.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_a),))
            cur.execute(
                "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
                (str(admin_a), "De A", email_repetido),
            )
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_b),))
            cur.execute(
                "INSERT INTO persona (administracion_id, nombre, email) VALUES (%s, %s, %s)",
                (str(admin_b), "De B", email_repetido),
            )
        conexion2.commit()
    finally:
        conexion2.close()


# --- downgrade a 0002 deja el esquema como estaba, y upgrade vuelve ---


def test_downgrade_a_0002_borra_las_tablas_y_upgrade_las_vuelve_a_crear(
    contenedor: PostgresContainer, esquema: None
) -> None:
    def _tablas_existen(nombres: set[str]) -> set[str]:
        conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
        try:
            with conexion.cursor() as cur:
                cur.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename = ANY(%s)",
                    (list(nombres),),
                )
                return {fila[0] for fila in cur.fetchall()}
        finally:
            conexion.close()

    tablas_0003 = {"administracion", "complejo", "unidad", "persona", "asignacion_rol"}
    assert _tablas_existen(tablas_0003) == tablas_0003

    _correr(["uv", "run", "alembic", "downgrade", "0002"], _alembic_env(contenedor))
    assert _tablas_existen(tablas_0003) == set()
    assert _tablas_existen({"trabajos_hechos"}) == {"trabajos_hechos"}

    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    assert _tablas_existen(tablas_0003) == tablas_0003
