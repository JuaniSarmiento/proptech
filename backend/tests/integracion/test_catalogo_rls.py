"""Guardián del catálogo (D5, cambio 2a, tarea 3.2): recorre `pg_catalog`
después de `upgrade head` y falla, nombrando la tabla, si alguna tabla de
`public` no cumple las tres reglas de D5.

Contenedor propio (L-006, nunca el de sesión). Los cinco rojos (L-013) usan
una tabla de prueba creada a mano con `CREATE TABLE`, nunca una migración
real: es la forma de ver al guardián fallar sin tocar el esquema real del
candado. Cada tabla de prueba se borra al final de su test.

Escenario de `aislamiento-por-administracion`: Una tabla nueva sin candado.
Lecciones: L-013, L-016.
"""

import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.roles import _TABLAS_DE_SOLO_AGREGAR

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

ARRANQUE_USER = "arranque_guardian"
ARRANQUE_PASSWORD = "clave-arranque-no-real"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"

#: D5: nunca se reasigna/exige administracion_id (son técnicas, o se aíslan
#: distinto, como `administracion`).
_TABLAS_TECNICAS = {"alembic_version", "trabajos_hechos", "accion_de_auditoria"}
#: D5/D6: sólo `asignacion_rol` admite complejo nulo para el alcance principal.
_EXCEPCIONES_COMPLEJO_ID_NULO = {"asignacion_rol"}

_PATRON_CURRENT_SETTING_DOS_ARGUMENTOS = re.compile(
    r"current_setting\(\s*'app\.administracion_id'(?:::text)?\s*,\s*true\s*\)", re.IGNORECASE
)

# Expresiones normalizadas por PostgreSQL (pg_get_expr), comparación completa D2/D6.
_EXCEPCIONES_DE_LECTURA = {
    ("public", "persona", "persona_por_identidad_clerk"): (
        "SELECT",
        "PERMISSIVE",
        ("public",),
        "((clerk_usuario_id = "
        "NULLIF(current_setting('app.identidad_clerk'::text, true), ''::text)) "
        "AND (NULLIF(current_setting('app.administracion_id'::text, true), ''::text) IS NULL))",
        None,
    ),
    ("public", "invitacion", "invitacion_por_token"): (
        "SELECT",
        "PERMISSIVE",
        ("public",),
        "((token_resumen = decode(NULLIF(current_setting('app.invitacion_token'::text, true), "
        "''::text), 'hex'::text)) AND "
        "(NULLIF(current_setting('app.administracion_id'::text, true), ''::text) IS NULL))",
        None,
    ),
}


# --- El guardián mismo ---


def _tablas_de_public(cur: psycopg.Cursor) -> list[str]:
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    return [fila[0] for fila in cur.fetchall()]


def _columnas(cur: psycopg.Cursor, tabla: str) -> dict[str, bool]:
    """Nombre de columna -> es nullable."""
    cur.execute(
        "SELECT column_name, is_nullable FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (tabla,),
    )
    return {fila[0]: fila[1] == "YES" for fila in cur.fetchall()}


def _rls_forzada(cur: psycopg.Cursor, tabla: str) -> bool:
    cur.execute(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
        "WHERE relname = %s AND relnamespace = 'public'::regnamespace",
        (tabla,),
    )
    fila = cur.fetchone()
    return fila is not None and bool(fila[0]) and bool(fila[1])


def _politicas_invalidas(cur: psycopg.Cursor, tabla: str) -> list[str]:
    cur.execute(
        "SELECT schemaname,tablename,policyname,cmd,permissive,roles,qual,with_check "
        "FROM pg_policies WHERE schemaname = 'public' AND tablename = %s",
        (tabla,),
    )
    filas = cur.fetchall()
    if not filas:
        return ["(ausente)"]
    invalidas = []
    for esquema, nombre_tabla, nombre, cmd, permisiva, roles, qual, with_check in filas:
        clave = (esquema, nombre_tabla, nombre)
        if clave in _EXCEPCIONES_DE_LECTURA:
            permitida = (cmd, permisiva, tuple(roles), qual, with_check) == _EXCEPCIONES_DE_LECTURA[
                clave
            ]
        else:
            # Regla ordinaria intacta: tenant de dos argumentos en ambos lados.
            permitida = bool(
                _PATRON_CURRENT_SETTING_DOS_ARGUMENTOS.search(qual or "")
                and _PATRON_CURRENT_SETTING_DOS_ARGUMENTOS.search(with_check or "")
            )
        if not permitida:
            invalidas.append(nombre)
    return invalidas


def _app_tiene_los_cuatro_permisos(cur: psycopg.Cursor, tabla: str) -> bool:
    cur.execute(
        "SELECT has_table_privilege(%s, %s, 'SELECT'), has_table_privilege(%s, %s, 'INSERT'), "
        "has_table_privilege(%s, %s, 'UPDATE'), has_table_privilege(%s, %s, 'DELETE')",
        (APP_USER, tabla, APP_USER, tabla, APP_USER, tabla, APP_USER, tabla),
    )
    fila = cur.fetchone()
    return fila is not None and all(fila)


def _tiene_fk_compuesta_a_complejo(cur: psycopg.Cursor, tabla: str) -> bool:
    cur.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE contype = 'f' AND conrelid = %s::regclass",
        (tabla,),
    )
    definiciones = [fila[0] for fila in cur.fetchall()]
    patron = re.compile(
        r"FOREIGN KEY \([^)]*\badministracion_id\b[^)]*\bcomplejo_id\b[^)]*\) "
        r"REFERENCES complejo\([^)]*\badministracion_id\b[^)]*\bid\b[^)]*\)"
    )
    return any(patron.search(definicion) for definicion in definiciones)


def _app_tiene_solo_select_insert(cur: psycopg.Cursor, tabla: str) -> bool:
    permisos = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
    return all(
        cur.execute("SELECT has_table_privilege(%s, %s, %s)", (APP_USER, tabla, permiso)).fetchone()
        == (permiso in {"SELECT", "INSERT"},)
        for permiso in permisos
    )


def _trigger_rechaza_update_como_app(cur: psycopg.Cursor, tabla: str) -> bool:
    """Dos capas independientes: permiso temporal sólo dentro del SAVEPOINT.

    El cursor de catálogo conecta como arranque para preparar la sonda; la
    escritura conecta por SET LOCAL ROLE a la app sin BYPASSRLS. Ni permiso,
    ni tenant, ni filas de prueba sobreviven al ROLLBACK.
    """
    cur.execute("SAVEPOINT sonda_solo_agregar")
    try:
        admin, complejo, persona = uuid4(), uuid4(), uuid4()
        cur.execute("SELECT set_config('app.administracion_id', %s, true)", (str(admin),))
        if tabla == "configuracion_versionada":
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, 'Sonda ficticia')", (admin,)
            )
            cur.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, 'Sonda ficticia', 'Mendoza')",
                (complejo, admin),
            )
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre) "
                "VALUES (%s, %s, 'Sonda ficticia')",
                (persona, admin),
            )
            cur.execute(
                "INSERT INTO configuracion_versionada "
                "(administracion_id, complejo_id, autor_id, vigente_desde, tasa_mensual, "
                "dias_de_gracia, forma_de_calculo, porcentaje_fondo, dia_de_vencimiento, "
                "modalidad_de_vencimiento) VALUES (%s, %s, %s, CURRENT_DATE, '3.00', 0, "
                "'proporcional_por_dia', '0.00', 10, 'unico')",
                (admin, complejo, persona),
            )
        else:
            cur.execute(
                sql.SQL("INSERT INTO {} (administracion_id) VALUES (%s)").format(
                    sql.Identifier(tabla)
                ),
                (admin,),
            )
        cur.execute(
            sql.SQL("GRANT UPDATE ON {} TO {}").format(
                sql.Identifier(tabla), sql.Identifier(APP_USER)
            )
        )
        cur.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(APP_USER)))
        assert cur.execute(
            "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == (APP_USER, False, False)
        try:
            cur.execute(
                sql.SQL("UPDATE {} SET administracion_id = administracion_id").format(
                    sql.Identifier(tabla)
                )
            )
        except psycopg.Error as error:
            return error.sqlstate == "P0001" and f"{tabla} no admite" in str(error)
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT sonda_solo_agregar")
        cur.execute("RELEASE SAVEPOINT sonda_solo_agregar")
    return False


def revisar_catalogo(cur: psycopg.Cursor) -> list[str]:
    """Las tres reglas de D5. Devuelve una lista de problemas, cada uno
    nombrando la tabla; vacía si todo cumple."""
    problemas: list[str] = []
    for tabla in _tablas_de_public(cur):
        columnas = _columnas(cur, tabla)

        if "administracion_id" in columnas or tabla == "administracion":
            columna_aislante = "id" if tabla == "administracion" else "administracion_id"
            if not _rls_forzada(cur, tabla):
                problemas.append(f"{tabla}: RLS no está activada y forzada")
            invalidas = _politicas_invalidas(cur, tabla)
            if invalidas:
                problemas.append(
                    f"{tabla}: política {', '.join(invalidas)} no cumple "
                    f"current_setting('app.administracion_id', "
                    f"true) sobre {columna_aislante}, o le falta el segundo argumento"
                )
            if tabla in _TABLAS_DE_SOLO_AGREGAR:
                if not _app_tiene_solo_select_insert(cur, tabla):
                    problemas.append(f"{tabla}: proptech_app debe tener exactamente SELECT/INSERT")
                if not _trigger_rechaza_update_como_app(cur, tabla):
                    problemas.append(f"{tabla}: el trigger no rechaza UPDATE como proptech_app")
            elif not _app_tiene_los_cuatro_permisos(cur, tabla):
                problemas.append(
                    f"{tabla}: proptech_app no tiene los permisos SELECT/INSERT/UPDATE/DELETE"
                )
        elif tabla not in _TABLAS_TECNICAS:
            problemas.append(f"{tabla}: no tiene administracion_id y no es una tabla técnica")

        if "complejo_id" in columnas and tabla not in _EXCEPCIONES_COMPLEJO_ID_NULO:
            if columnas["complejo_id"]:
                problemas.append(f"{tabla}: complejo_id admite NULL")
            if not _tiene_fk_compuesta_a_complejo(cur, tabla):
                problemas.append(
                    f"{tabla}: no tiene la FK compuesta (administracion_id, complejo_id) "
                    f"-> complejo (administracion_id, id)"
                )

    return problemas


# --- Fixtures: contenedor propio, roles reales, esquema migrado ---


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


def _conectar_como_migrador(contenedor: PostgresContainer) -> psycopg.Connection:
    conexion = psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
        dbname=contenedor.dbname,
        autocommit=True,
    )
    return conexion


# --- El esquema real pasa limpio ---


def test_el_esquema_real_no_tiene_ningun_problema(
    contenedor: PostgresContainer, esquema: None
) -> None:
    problemas = _revisar_como_arranque(contenedor)
    assert problemas == []


def _revisar_como_arranque(contenedor: PostgresContainer) -> list[str]:
    with (
        psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            user=ARRANQUE_USER,
            password=ARRANQUE_PASSWORD,
            dbname=contenedor.dbname,
        ) as conexion,
        conexion.cursor() as cur,
    ):
        return revisar_catalogo(cur)


# --- Los cinco rojos (L-013): una tabla de prueba por escenario, nunca la migración real ---


def _crear_y_revisar(contenedor: PostgresContainer, nombre_tabla: str, ddl: list[str]) -> list[str]:
    conexion = _conectar_como_migrador(contenedor)
    try:
        with conexion.cursor() as cur:
            for sentencia in ddl:
                cur.execute(sentencia)
            problemas = _revisar_como_arranque(contenedor)
    finally:
        with conexion.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{nombre_tabla}"')
        conexion.close()
    return problemas


#: La condición de D5, completa (USING y WITH CHECK): se reusa en los
#: escenarios que no están probando el formato de la política misma, así
#: cada rojo aísla un solo defecto (Postgres no copia USING a WITH CHECK
#: si no se lo pide explícitamente: una política sin WITH CHECK queda con
#: `with_check = NULL`, y eso es "no tiene política" para el guardián).
def _condicion_valida(columna: str = "administracion_id") -> str:
    return f"{columna} = nullif(current_setting('app.administracion_id', true), '')::uuid"


def test_rojo_tabla_sin_force(contenedor: PostgresContainer, esquema: None) -> None:
    tabla = "zz_prueba_sin_force"
    condicion = _condicion_valida()
    problemas = _crear_y_revisar(
        contenedor,
        tabla,
        [
            f'CREATE TABLE "{tabla}" (administracion_id uuid NOT NULL)',
            f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',  # sin FORCE, a propósito
            f'CREATE POLICY "{tabla}_por_administracion" ON "{tabla}" '
            f"USING ({condicion}) WITH CHECK ({condicion})",
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON "{tabla}" TO {APP_USER}',
        ],
    )
    assert any(tabla in p and "forzada" in p for p in problemas), problemas
    assert not any(tabla in p and "política" in p for p in problemas), problemas
    assert not any(tabla in p and "permisos" in p for p in problemas), problemas


def test_rojo_tabla_sin_politica(contenedor: PostgresContainer, esquema: None) -> None:
    tabla = "zz_prueba_sin_politica"
    problemas = _crear_y_revisar(
        contenedor,
        tabla,
        [
            f'CREATE TABLE "{tabla}" (administracion_id uuid NOT NULL)',
            f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY',
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON "{tabla}" TO {APP_USER}',
        ],
    )
    assert any(tabla in p and "política" in p for p in problemas), problemas
    assert not any(tabla in p and "forzada" in p for p in problemas), problemas


def test_rojo_politica_con_current_setting_de_un_solo_argumento(
    contenedor: PostgresContainer, esquema: None
) -> None:
    tabla = "zz_prueba_un_argumento"
    # Un solo argumento en los dos lados (USING y WITH CHECK): sin
    # missing_ok, revienta si la variable nunca se fijó, en vez de dar cero
    # filas (D5).
    condicion_rota = (
        "administracion_id = nullif(current_setting('app.administracion_id'), '')::uuid"
    )
    problemas = _crear_y_revisar(
        contenedor,
        tabla,
        [
            f'CREATE TABLE "{tabla}" (administracion_id uuid NOT NULL)',
            f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY',
            f'CREATE POLICY "{tabla}_por_administracion" ON "{tabla}" '
            f"USING ({condicion_rota}) WITH CHECK ({condicion_rota})",
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON "{tabla}" TO {APP_USER}',
        ],
    )
    assert any(tabla in p and "política" in p for p in problemas), problemas
    assert not any(tabla in p and "forzada" in p for p in problemas), problemas


def test_rojo_tabla_sin_grant(contenedor: PostgresContainer, esquema: None) -> None:
    tabla = "zz_prueba_sin_grant"
    condicion = _condicion_valida()
    problemas = _crear_y_revisar(
        contenedor,
        tabla,
        [
            f'CREATE TABLE "{tabla}" (administracion_id uuid NOT NULL)',
            f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY',
            f'CREATE POLICY "{tabla}_por_administracion" ON "{tabla}" '
            f"USING ({condicion}) WITH CHECK ({condicion})",
            # Sin GRANT explícito; además REVOKE de lo que los DEFAULT
            # PRIVILEGES de roles.py ya le hayan dado de regalo (si no, este
            # rojo no prueba nada, L-016).
            f'REVOKE ALL ON "{tabla}" FROM {APP_USER}',
        ],
    )
    assert any(tabla in p and "permisos" in p for p in problemas), problemas
    assert not any(tabla in p and "forzada" in p for p in problemas), problemas
    assert not any(tabla in p and "no tiene política" in p for p in problemas), problemas


def test_rojo_complejo_id_nulo_o_sin_fk(contenedor: PostgresContainer, esquema: None) -> None:
    tabla = "zz_prueba_complejo_nulo"
    condicion = _condicion_valida()
    problemas = _crear_y_revisar(
        contenedor,
        tabla,
        [
            # complejo_id NULLABLE y sin la FK compuesta, a propósito.
            f'CREATE TABLE "{tabla}" (administracion_id uuid NOT NULL, complejo_id uuid)',
            f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY',
            f'CREATE POLICY "{tabla}_por_administracion" ON "{tabla}" '
            f"USING ({condicion}) WITH CHECK ({condicion})",
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON "{tabla}" TO {APP_USER}',
        ],
    )
    assert any(tabla in p and "complejo_id" in p for p in problemas), problemas
    assert not any(tabla in p and "forzada" in p for p in problemas), problemas
    assert not any(tabla in p and "no tiene política" in p for p in problemas), problemas


@pytest.mark.parametrize(
    "defecto", ["ninguno", "sin_trigger", "trigger_inerte", "permiso_extra", "sin_insert"]
)
def test_excepcion_solo_agregar_exige_permisos_exactos_y_bloqueo_real(
    contenedor: PostgresContainer, esquema: None, monkeypatch: pytest.MonkeyPatch, defecto: str
) -> None:
    tabla = "zz_solo_agregar"
    monkeypatch.setitem(globals(), "_TABLAS_DE_SOLO_AGREGAR", frozenset({tabla}))
    condicion = _condicion_valida()
    ddl = [
        f'CREATE TABLE "{tabla}" (id uuid DEFAULT gen_random_uuid(), '
        "administracion_id uuid NOT NULL)",
        f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',
        f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY',
        f'CREATE POLICY aislamiento ON "{tabla}" USING ({condicion}) WITH CHECK ({condicion})',
        f'REVOKE ALL ON "{tabla}" FROM {APP_USER}',
        f'GRANT SELECT, INSERT ON "{tabla}" TO {APP_USER}',
    ]
    if defecto != "sin_trigger":
        cuerpo = (
            "RETURN NEW;"
            if defecto == "trigger_inerte"
            else f"RAISE EXCEPTION '{tabla} no admite cambios';"
        )
        ddl += [
            "CREATE OR REPLACE FUNCTION fn_sonda() RETURNS trigger LANGUAGE plpgsql "
            f"AS $$ BEGIN {cuerpo} END $$",
            f'CREATE TRIGGER bloqueo BEFORE UPDATE ON "{tabla}" '
            "FOR EACH ROW EXECUTE FUNCTION fn_sonda()",
        ]
    if defecto == "permiso_extra":
        ddl.append(f'GRANT TRUNCATE ON "{tabla}" TO {APP_USER}')
    if defecto == "sin_insert":
        ddl.append(f'REVOKE INSERT ON "{tabla}" FROM {APP_USER}')
    try:
        problemas = [
            p for p in _crear_y_revisar(contenedor, tabla, ddl) if p.startswith(f"{tabla}:")
        ]
    finally:
        with _conectar_como_migrador(contenedor) as conexion:
            conexion.execute("DROP FUNCTION IF EXISTS fn_sonda()")
    if defecto == "ninguno":
        assert problemas == []
    elif defecto in {"sin_trigger", "trigger_inerte"}:
        assert any("trigger" in p for p in problemas), problemas
    else:
        assert any("exactamente SELECT/INSERT" in p for p in problemas), problemas


def test_tabla_fuera_de_la_lista_con_solo_select_insert_se_rechaza(
    contenedor: PostgresContainer, esquema: None
) -> None:
    tabla = "zz_ordinaria_con_permisos_incompletos"
    condicion = _condicion_valida()
    problemas = _crear_y_revisar(
        contenedor,
        tabla,
        [
            f'CREATE TABLE "{tabla}" (administracion_id uuid NOT NULL)',
            f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY',
            f'CREATE POLICY aislamiento ON "{tabla}" USING ({condicion}) WITH CHECK ({condicion})',
            f'REVOKE ALL ON "{tabla}" FROM {APP_USER}',
            f'GRANT SELECT, INSERT ON "{tabla}" TO {APP_USER}',
        ],
    )
    assert problemas == [f"{tabla}: proptech_app no tiene los permisos SELECT/INSERT/UPDATE/DELETE"]


@pytest.mark.parametrize(
    "defecto", ["otra_tabla", "qual", "cmd", "roles", "restrictiva", "nombre", "with_check"]
)
def test_lista_blanca_rechaza_politicas_parecidas(
    contenedor: PostgresContainer, esquema: None, defecto: str
) -> None:
    tabla = "complejo" if defecto == "otra_tabla" else "persona"
    nombre = "otra_identidad" if defecto == "nombre" else "persona_por_identidad_clerk"
    condicion = ("nombre" if defecto == "otra_tabla" else "clerk_usuario_id") + (
        " = nullif(current_setting('app.identidad_clerk',true),'') AND "
        "nullif(current_setting('app.administracion_id',true),'') IS NULL"
    )
    if defecto == "qual":
        condicion += " OR true"
    with (
        psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=ARRANQUE_USER,
            password=ARRANQUE_PASSWORD,
        ) as conexion,
        conexion.cursor() as cur,
    ):
        try:
            cur.execute("DROP POLICY persona_por_identidad_clerk ON persona")
            cur.execute(
                sql.SQL("CREATE POLICY {} ON {} AS {} FOR {} TO {} USING ({})").format(
                    sql.Identifier(nombre),
                    sql.Identifier(tabla),
                    sql.SQL("RESTRICTIVE" if defecto == "restrictiva" else "PERMISSIVE"),
                    sql.SQL("ALL" if defecto == "cmd" else "SELECT"),
                    sql.Identifier(APP_USER) if defecto == "roles" else sql.SQL("PUBLIC"),
                    sql.SQL(condicion),
                )
            )
            if defecto == "with_check":
                # Estado de catálogo hostil: DDL no permite WITH CHECK en SELECT.
                # Sólo esta transacción del contenedor; rollback en finally.
                cur.execute(
                    "UPDATE pg_policy SET polwithcheck=polqual "
                    "WHERE polrelid='persona'::regclass AND polname='persona_por_identidad_clerk'"
                )
            problemas = revisar_catalogo(cur)
            assert any(tabla in p and nombre in p for p in problemas), problemas
        finally:
            conexion.rollback()


@pytest.mark.parametrize("defecto", ["qual", "cmd", "roles", "restrictiva", "nombre", "with_check"])
def test_lista_blanca_de_invitacion_es_exacta(
    contenedor: PostgresContainer, esquema: None, defecto: str
) -> None:
    nombre = "otra_por_token" if defecto == "nombre" else "invitacion_por_token"
    condicion = (
        "token_resumen = decode(nullif(current_setting('app.invitacion_token',true),''),'hex') AND "
        "nullif(current_setting('app.administracion_id',true),'') IS NULL"
    )
    if defecto == "qual":
        condicion += " OR true"
    with (
        psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=ARRANQUE_USER,
            password=ARRANQUE_PASSWORD,
        ) as conexion,
        conexion.cursor() as cur,
    ):
        try:
            cur.execute("DROP POLICY invitacion_por_token ON invitacion")
            cur.execute(
                sql.SQL("CREATE POLICY {} ON invitacion AS {} FOR {} TO {} USING ({})").format(
                    sql.Identifier(nombre),
                    sql.SQL("RESTRICTIVE" if defecto == "restrictiva" else "PERMISSIVE"),
                    sql.SQL("ALL" if defecto == "cmd" else "SELECT"),
                    sql.Identifier(APP_USER) if defecto == "roles" else sql.SQL("PUBLIC"),
                    sql.SQL(condicion),
                )
            )
            if defecto == "with_check":
                cur.execute(
                    "UPDATE pg_policy SET polwithcheck=polqual "
                    "WHERE polrelid='invitacion'::regclass AND polname='invitacion_por_token'"
                )
            problemas = revisar_catalogo(cur)
            assert any("invitacion" in p and nombre in p for p in problemas), problemas
        finally:
            conexion.rollback()
