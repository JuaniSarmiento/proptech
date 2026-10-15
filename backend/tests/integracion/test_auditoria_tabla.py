"""Migración `0004_auditoria` y paso de roles `despues` (D2, D9, cambio 2a,
tarea 6.1) contra PostgreSQL real.

Contenedor propio (L-006, nunca el de sesión). Dos escenarios necesitan un
contenedor dedicado DISTINTO del principal:

- El rojo de `test_rojo_sin_el_paso_despues_...`: sin correr `roles despues`,
  el migrador sigue siendo dueño de `auditoria` (puede desactivar el trigger
  y el `FORCE`) y `proptech_app` tiene de más el `UPDATE`/`DELETE` que le
  regalan los `ALTER DEFAULT PRIVILEGES` de `antes()` (L-013, L-016): es la
  prueba de que, sin el paso `despues`, D9 no se cumple.
- El de `downgrade`/`upgrade`: baja y sube el esquema sobre el contenedor
  principal, pero necesita devolverle `auditoria` al migrador antes de poder
  bajarla (D9, D11: el migrador no es dueño después de `despues`).

Escenarios de `auditoria-de-acciones`: Editar o borrar como la app; Editar,
borrar o desactivar el bloqueo como el migrador; Editar o borrar como el
dueño; Dueño de la tabla después de las migraciones; Acción fuera de la
lista; Auditoría de otra administración. Lecciones: L-013, L-016.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.acceso.dominio.permisos import Accion

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_auditoria"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"

_ACCION_DE_PRUEBA = Accion.INFORMAR_PAGO.value


# --- Entorno, roles reales y ciclo de migraciones (igual al resto de 3.x/4.x/5.x) ---


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


def _correr_falla(args: list[str], entorno: dict[str, str]) -> subprocess.CalledProcessError:
    """Como `_correr`, pero para los casos donde el comando DEBE fallar
    (L-016): devuelve el error en vez de dejarlo pasar en silencio."""
    resultado = subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, capture_output=True, text=True)
    assert resultado.returncode != 0, (
        f"se esperaba que el comando fallara y no falló: {' '.join(args)}\n{resultado.stdout}"
    )
    return subprocess.CalledProcessError(
        resultado.returncode, args, resultado.stdout, resultado.stderr
    )


def _conectar(contenedor: PostgresContainer, usuario: str, password: str) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario,
        password=password,
        dbname=contenedor.dbname,
        autocommit=True,
    )


def _devolver_auditoria_al_migrador(contenedor: PostgresContainer) -> None:
    """D9/D11: el migrador no es dueño de `auditoria` después de `despues()`,
    así que no puede bajarla con `alembic downgrade`. Se la devuelve antes,
    con el rol de arranque — exactamente lo que el Migration Plan del
    design.md deja como procedimiento manual y deliberado.

    Desde R2 (vuelta 2), lo mismo vale para la función del trigger: el
    `downgrade` de la migración 0004 hace `DROP FUNCTION
    fn_auditoria_bloqueada()` como migrador, y ya no es su dueña."""
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT to_regclass('public.auditoria') IS NOT NULL")
            fila = cur.fetchone()
            if fila is not None and fila[0]:
                cur.execute(f"ALTER TABLE auditoria OWNER TO {MIGRADOR_USER}")
                for funcion in _funciones_de_los_triggers_de_auditoria(cur):
                    cur.execute(f"ALTER FUNCTION {funcion}() OWNER TO {MIGRADOR_USER}")
    finally:
        conexion.close()


def _funciones_de_los_triggers_de_auditoria(cur: psycopg.Cursor) -> list[str]:
    cur.execute(
        "SELECT DISTINCT p.proname FROM pg_trigger t "
        "JOIN pg_proc p ON p.oid = t.tgfoid "
        "WHERE t.tgrelid = 'auditoria'::regclass AND NOT t.tgisinternal"
    )
    return [fila[0] for fila in cur.fetchall()]


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        _entorno_de_roles(contenedor),
    )
    try:
        yield
    finally:
        _devolver_auditoria_al_migrador(contenedor)
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


def _sembrar_fila(
    contenedor: PostgresContainer, *, administracion_id: uuid.UUID, accion: str = _ACCION_DE_PRUEBA
) -> None:
    """Inserta una fila con el rol de arranque (superusuario: bypassea la
    política sin necesitar fijar tenant), para los tests que necesitan una
    fila YA existente que el trigger de fila pueda interceptar."""
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "INSERT INTO auditoria "
                "(administracion_id, persona_id, accion, entidad, entidad_id, request_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    str(administracion_id),
                    str(uuid.uuid4()),
                    accion,
                    "complejo",
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                ),
            )
    finally:
        conexion.close()


# --- Dueño de la tabla después de las migraciones ---


def test_el_dueño_de_auditoria_es_el_rol_de_arranque(
    contenedor: PostgresContainer, esquema: None
) -> None:
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT tableowner FROM pg_tables WHERE tablename = 'auditoria'")
            assert cur.fetchone() == (ARRANQUE_USER,)
    finally:
        conexion.close()


# --- Vuelta 2, R2: la función de los triggers también es del rol de arranque ---


def test_el_dueño_de_fn_auditoria_bloqueada_es_el_rol_de_arranque(
    contenedor: PostgresContainer, esquema: None
) -> None:
    """Catálogo, no un nombre fijo (pedido del auditor): recorre los
    triggers reales de `auditoria` y pide el dueño de CADA función que
    disparan, para que esto siga valiendo si el día de mañana se agrega
    otro trigger con otra función. `despues()` transfería la tabla pero no
    la función (D9 lo pide, D2 también): sin esto, el migrador sigue siendo
    dueño de la función que hace cumplir el bloqueo, y dueño de una función
    alcanza para reemplazarla o borrarla."""
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT pg_get_userbyid(p.proowner) "
                "FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
                "WHERE t.tgrelid = 'auditoria'::regclass AND NOT t.tgisinternal"
            )
            dueños = {fila[0] for fila in cur.fetchall()}
    finally:
        conexion.close()
    assert dueños == {ARRANQUE_USER}, dueños


def test_el_migrador_no_puede_reemplazar_ni_borrar_la_funcion_del_trigger(
    contenedor: PostgresContainer, esquema: None
) -> None:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    conexion.autocommit = False
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(
                    "CREATE OR REPLACE FUNCTION fn_auditoria_bloqueada() "
                    "RETURNS trigger AS $$ BEGIN RETURN NULL; END; $$ LANGUAGE plpgsql"
                )
        conexion.rollback()
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute("DROP FUNCTION fn_auditoria_bloqueada() CASCADE")
    finally:
        conexion.rollback()
        conexion.close()


# --- La app sólo tiene SELECT e INSERT (D9): el REVOKE explícito de despues() ---


def test_la_app_tiene_exactamente_select_e_insert_sobre_auditoria(
    contenedor: PostgresContainer, esquema: None
) -> None:
    """Chequeo directo por privilegio (no por un DML que el trigger también
    bloquearía, enmascarando si el privilegio seguía o no ahí): sin el
    `REVOKE` explícito de `despues()`, `UPDATE`/`DELETE` quedan en `True`
    por los `ALTER DEFAULT PRIVILEGES` de `antes()` (ver el rojo de
    `test_rojo_sin_despues_...`)."""
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT has_table_privilege(%s, 'auditoria', 'SELECT'), "
                "has_table_privilege(%s, 'auditoria', 'INSERT'), "
                "has_table_privilege(%s, 'auditoria', 'UPDATE'), "
                "has_table_privilege(%s, 'auditoria', 'DELETE'), "
                "has_table_privilege(%s, 'auditoria', 'TRUNCATE')",
                (APP_USER, APP_USER, APP_USER, APP_USER, APP_USER),
            )
            fila = cur.fetchone()
            assert fila is not None
            puede_select, puede_insert, puede_update, puede_delete, puede_truncate = fila
    finally:
        conexion.close()
    assert puede_select is True
    assert puede_insert is True
    assert puede_update is False
    assert puede_delete is False
    assert puede_truncate is False


# --- Editar o borrar como la app ---


@pytest.mark.parametrize(
    "sentencia", ["UPDATE auditoria SET entidad = 'x'", "DELETE FROM auditoria"]
)
def test_editar_o_borrar_como_la_app_falla(
    contenedor: PostgresContainer, esquema: None, sentencia: str
) -> None:
    conexion = _conectar(contenedor, APP_USER, APP_PASSWORD)
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(sentencia)
    finally:
        conexion.close()


def test_truncate_como_la_app_falla(contenedor: PostgresContainer, esquema: None) -> None:
    conexion = _conectar(contenedor, APP_USER, APP_PASSWORD)
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute("TRUNCATE auditoria")
    finally:
        conexion.close()


# --- Editar, borrar o desactivar el bloqueo como el migrador (no es dueño) ---


@pytest.mark.parametrize(
    "sentencia",
    [
        "UPDATE auditoria SET entidad = 'x'",
        "DELETE FROM auditoria",
        "TRUNCATE auditoria",
        "ALTER TABLE auditoria DISABLE TRIGGER ALL",
        "ALTER TABLE auditoria NO FORCE ROW LEVEL SECURITY",
    ],
)
def test_editar_borrar_o_desactivar_el_bloqueo_como_el_migrador_falla_por_no_ser_dueño(
    contenedor: PostgresContainer, esquema: None, sentencia: str
) -> None:
    conexion = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(sentencia)
    finally:
        conexion.close()


def test_el_trigger_y_el_force_siguen_activos_tras_el_intento_del_migrador(
    contenedor: PostgresContainer, esquema: None
) -> None:
    # El intento de ALTER del test anterior falló (no es dueño): esto
    # confirma que el estado de verdad (no sólo el error devuelto) sigue
    # intacto.
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname = 'auditoria' AND relnamespace = 'public'::regnamespace"
            )
            fila_rls = cur.fetchone()
            assert fila_rls is not None
            rls, forzada = fila_rls
            assert rls is True
            assert forzada is True
            cur.execute(
                "SELECT tgenabled FROM pg_trigger WHERE tgrelid = 'auditoria'::regclass "
                "AND tgname = 'trg_auditoria_sin_update_delete'"
            )
            fila_trigger = cur.fetchone()
            assert fila_trigger is not None
            assert fila_trigger[0] == "O"  # "O" = origin, trigger habilitado (no "D" = disabled)
    finally:
        conexion.close()


# --- Editar o borrar como el dueño (el trigger lo bloquea igual) ---


def test_editar_o_borrar_como_el_dueño_falla_por_el_trigger(
    contenedor: PostgresContainer, esquema: None
) -> None:
    administracion_id = uuid.uuid4()
    _sembrar_fila(contenedor, administracion_id=administracion_id)

    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    conexion.autocommit = False
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "UPDATE auditoria SET entidad = 'x' WHERE administracion_id = %s",
                    (str(administracion_id),),
                )
        conexion.rollback()
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "DELETE FROM auditoria WHERE administracion_id = %s", (str(administracion_id),)
                )
    finally:
        conexion.rollback()
        conexion.close()


def test_truncate_como_el_dueño_falla_por_el_trigger(
    contenedor: PostgresContainer, esquema: None
) -> None:
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("TRUNCATE auditoria")
    finally:
        conexion.close()


# --- Acción fuera de la lista: falla por la FK ---


def test_una_accion_que_no_está_en_accion_de_auditoria_falla_por_fk(
    contenedor: PostgresContainer, esquema: None
) -> None:
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    conexion.autocommit = False
    try:
        with conexion.cursor() as cur:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                cur.execute(
                    "INSERT INTO auditoria "
                    "(administracion_id, persona_id, accion, entidad, entidad_id, request_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        str(uuid.uuid4()),
                        str(uuid.uuid4()),
                        "esta_accion_no_existe",
                        "complejo",
                        str(uuid.uuid4()),
                        str(uuid.uuid4()),
                    ),
                )
    finally:
        conexion.rollback()
        conexion.close()


def test_accion_de_auditoria_coincide_con_accion(
    contenedor: PostgresContainer, esquema: None
) -> None:
    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT nombre FROM accion_de_auditoria")
            en_la_tabla = {fila[0] for fila in cur.fetchall()}
    finally:
        conexion.close()
    assert en_la_tabla == {accion.value for accion in Accion}


# --- Auditoría de otra administración: RLS de D5 también aplica acá ---


def test_con_el_tenant_de_a_no_aparece_ninguna_fila_de_b(
    contenedor: PostgresContainer, esquema: None
) -> None:
    administracion_a = uuid.uuid4()
    administracion_b = uuid.uuid4()
    _sembrar_fila(contenedor, administracion_id=administracion_a)
    _sembrar_fila(contenedor, administracion_id=administracion_b)

    conexion = _conectar(contenedor, APP_USER, APP_PASSWORD)
    conexion.autocommit = False
    try:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.administracion_id', %s, false)", (str(administracion_a),)
            )
            cur.execute("SELECT administracion_id FROM auditoria")
            filas = {fila[0] for fila in cur.fetchall()}
            assert filas == {administracion_a}
            assert administracion_b not in filas
    finally:
        conexion.rollback()
        conexion.close()


# --- El rojo (L-013, L-016): sin el paso `despues`, nada de esto se cumple ---


def test_rojo_sin_despues_el_migrador_desarma_la_auditoria_y_la_app_tiene_de_mas() -> None:
    """Sin `despues()`, el migrador (dueño transitorio) puede desactivar el
    trigger y el `FORCE`, y `proptech_app` tiene `UPDATE`/`DELETE` de más
    sobre `auditoria` por los `ALTER DEFAULT PRIVILEGES` de `antes()` — el
    supuesto que quedó anotado en la 3.2 y que el REVOKE de `despues()`
    tiene que cerrar. `TRUNCATE` de la app falla de todos modos: nunca
    estuvo en la lista de los `ALTER DEFAULT PRIVILEGES` (sólo
    `SELECT, INSERT, UPDATE, DELETE`), así que no hace falta revocarlo para
    ver esto en rojo — se verifica para no asumirlo (L-016).

    `DISABLE TRIGGER` nombra el trigger propio, nunca `ALL`: un hallazgo real
    al escribir este test es que `ALL` incluye el trigger interno de la FK
    de `accion` (`RI_ConstraintTrigger_...`), y Postgres exige superusuario
    para desactivar ESE trigger puntual sin importar quién sea el dueño de
    la tabla — falla igual si el migrador es dueño o no, así que no sirve
    para distinguir el caso. El test principal (`falla_por_no_ser_dueño`)
    sí usa `ALL` porque ahí migrador ya NO es dueño: el "must be owner"
    llega antes de que Postgres mire qué triggers hay, y falla por la razón
    correcta."""
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as contenedor:
        _correr(
            [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
            _entorno_de_roles(contenedor),
        )
        _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
        # A propósito: NUNCA se corre "roles despues" en este contenedor.

        conexion_arranque = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
        try:
            with conexion_arranque.cursor() as cur:
                cur.execute("SELECT tableowner FROM pg_tables WHERE tablename = 'auditoria'")
                assert cur.fetchone() == (MIGRADOR_USER,), "el migrador debería seguir siendo dueño"
        finally:
            conexion_arranque.close()

        conexion_migrador = _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD)
        conexion_migrador.autocommit = False
        try:
            with conexion_migrador.cursor() as cur:
                # Nombrado, no ALL (ver docstring): esto sí levanta "must be
                # owner" si migrador no fuera dueño, y es justo lo que
                # queremos ver NO levantar acá.
                cur.execute("ALTER TABLE auditoria DISABLE TRIGGER trg_auditoria_sin_update_delete")
                cur.execute("ALTER TABLE auditoria NO FORCE ROW LEVEL SECURITY")  # no levanta
        finally:
            conexion_migrador.rollback()
            conexion_migrador.close()

        # Por privilegio, no por DML real: un UPDATE/DELETE real lo frena
        # igual el trigger (que acá sigue activo: el DISABLE de arriba se
        # revirtió con el rollback), así que un DML exitoso o fallido no
        # distingue si el privilegio está o no — el catálogo sí (L-016).
        conexion_arranque2 = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
        try:
            with conexion_arranque2.cursor() as cur:
                cur.execute(
                    "SELECT has_table_privilege(%s, 'auditoria', 'UPDATE'), "
                    "has_table_privilege(%s, 'auditoria', 'DELETE'), "
                    "has_table_privilege(%s, 'auditoria', 'TRUNCATE')",
                    (APP_USER, APP_USER, APP_USER),
                )
                fila = cur.fetchone()
                assert fila is not None
                puede_update, puede_delete, puede_truncate = fila
        finally:
            conexion_arranque2.close()
        # El sobre-otorgamiento real: UPDATE/DELETE de más por los ALTER
        # DEFAULT PRIVILEGES de antes(), sin el REVOKE de despues().
        assert puede_update is True
        assert puede_delete is True
        # TRUNCATE nunca estuvo en esa lista: falla igual, con o sin despues().
        assert puede_truncate is False

        _correr(["uv", "run", "alembic", "downgrade", "0003"], _alembic_env(contenedor))
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


# --- downgrade (con el rol de arranque) y upgrade vuelven ---


def test_downgrade_de_0004_exige_el_rol_de_arranque_y_upgrade_la_vuelve_a_crear(
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

    tablas_0004 = {"accion_de_auditoria", "auditoria"}
    assert _tablas_existen(tablas_0004) == tablas_0004

    # El migrador solo no puede: no es dueño de auditoria (D9/D11).
    _correr_falla(["uv", "run", "alembic", "downgrade", "0003"], _alembic_env(contenedor))
    assert _tablas_existen(tablas_0004) == tablas_0004  # nada se movió

    # Con el rol de arranque devolviéndosela al migrador primero, sí.
    _devolver_auditoria_al_migrador(contenedor)
    _correr(["uv", "run", "alembic", "downgrade", "0003"], _alembic_env(contenedor))
    assert _tablas_existen(tablas_0004) == set()

    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    assert _tablas_existen(tablas_0004) == tablas_0004
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        _entorno_de_roles(contenedor),
    )

    conexion = _conectar(contenedor, ARRANQUE_USER, ARRANQUE_PASSWORD)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT tableowner FROM pg_tables WHERE tablename = 'auditoria'")
            assert cur.fetchone() == (ARRANQUE_USER,)
    finally:
        conexion.close()
