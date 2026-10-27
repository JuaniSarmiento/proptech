"""E11: migrar funciones restauradas y devolver la protección al arrancar."""

import subprocess
import sys

import psycopg
from psycopg import sql
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

from .test_catalogo_rls import (  # noqa: F401
    ARRANQUE_USER,
    MIGRADOR_PASSWORD,
    MIGRADOR_USER,
    RAIZ_BACKEND,
    _alembic_env,
    _correr,
    _entorno_de_roles,
    contenedor,
)


def test_migracion_de_funciones_restauradas_y_proteccion(contenedor: PostgresContainer) -> None:  # noqa: F811
    entorno = _entorno_de_roles(contenedor)
    roles = [sys.executable, "-m", "proptech_core.compartido.roles"]
    _correr([*roles, "antes"], entorno)
    _correr(["uv", "run", "alembic", "upgrade", "0026"], _alembic_env(contenedor))
    with psycopg.connect(
        contenedor.get_connection_url().replace("postgresql+psycopg", "postgresql")
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.oid::regprocedure::text FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid=p.pronamespace "
                "WHERE n.nspname='public' AND p.prokind='f'"
            )
            for (firma,) in cur.fetchall():
                cur.execute(
                    sql.SQL("ALTER FUNCTION {} OWNER TO {}").format(
                        sql.SQL(firma), sql.Identifier(ARRANQUE_USER)
                    )
                )
    _correr([*roles, "antes"], entorno)
    resultado = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=_alembic_env(contenedor),
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    resultado = subprocess.run(
        [*roles, "despues"], cwd=RAIZ_BACKEND, env=entorno, capture_output=True, text=True
    )
    assert resultado.returncode == 0, resultado.stderr
    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        dbname=contenedor.dbname,
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT p.oid::regprocedure::text FROM pg_trigger t "
                "JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_class c ON c.oid=t.tgrelid "
                "WHERE c.relname = ANY(%s) AND NOT t.tgisinternal",
                (list(TABLAS_DE_SOLO_AGREGAR),),
            )
            funciones = [fila[0] for fila in cur.fetchall()]
            assert funciones
            for funcion in funciones:
                try:
                    with conn.transaction():
                        cur.execute(
                            sql.SQL("ALTER FUNCTION {} OWNER TO {}").format(
                                sql.SQL(funcion), sql.Identifier(MIGRADOR_USER)
                            )
                        )
                except psycopg.errors.InsufficientPrivilege:
                    continue
                raise AssertionError(f"migrador es dueño de {funcion}")
