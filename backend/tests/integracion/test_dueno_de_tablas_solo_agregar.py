"""D1/L-036: todas las tablas de la declaración única rechazan NO FORCE como migrador."""

import sys

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

# `contenedor` se importa para que pytest lo vea como fixture propia de este
# módulo (mismo patrón que usan entre sí los módulos de
# `tests/integracion/`); ruff no reconoce ese uso y marca el import y el
# parámetro de nombre igual como no usados/redefinidos (F401/F811).
# `esquema` NO se importa: este módulo define su propia versión (más abajo),
# que corre `despues()` además de migrar — sin eso, `auditoria` se queda con
# el dueño que le tocó al crearla (el migrador) y nunca se transfiere de
# vuelta al rol de arranque (D9), y el caso `auditoria` no representaría el
# estado realmente protegido.
from .test_catalogo_rls import (  # noqa: F401
    MIGRADOR_PASSWORD,
    MIGRADOR_USER,
    _alembic_env,
    _correr,
    _entorno_de_roles,
    contenedor,
)

pytestmark = pytest.mark.integracion

#: El mensaje exacto que Postgres da ante un `ALTER TABLE ... NO FORCE ROW
#: LEVEL SECURITY` corrido por un rol que no es dueño de la tabla (nunca
#: "cualquier error", mismo criterio que `roles._es_el_bloqueo_esperado`):
#: sin este chequeo de texto, cualquier otro motivo de
#: `InsufficientPrivilege` (un rol sin `USAGE` sobre el esquema, por ejemplo)
#: se confundiría con "no es dueño".
_MENSAJE_DE_NO_SER_DUENIO = "must be owner"


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> None:  # noqa: F811
    """Deploy real y segundo antes: ninguna protegida vuelve al migrador.

    Sin downgrade: la base pertenece sólo al contenedor descartable de este módulo.
    """
    entorno = _entorno_de_roles(contenedor)
    roles_cmd = [sys.executable, "-m", "proptech_core.compartido.roles"]
    _correr([*roles_cmd, "antes"], entorno)
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    _correr([*roles_cmd, "despues"], entorno)
    _correr([*roles_cmd, "antes"], entorno)


def _migrador_puede_quitar_el_force_rls(
    contenedor: PostgresContainer,  # noqa: F811
    tabla: str,
) -> bool:
    """True si, conectado como `proptech_migrador`, `NO FORCE ROW LEVEL
    SECURITY` sobre `tabla` tiene éxito. En PostgreSQL sólo el DUEÑO de una
    tabla puede hacer eso, nunca un rol con GRANT por fuera de la propiedad
    (ni siquiera con los cuatro permisos): por eso esta sonda, y no una
    lectura de catálogo, es el discriminante real (DBA-1).

    Corre dentro de su propia transacción y siempre hace ROLLBACK al final,
    gane o pierda la aserción: nunca deja el FORCE real desactivado para el
    resto de la corrida."""
    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        dbname=contenedor.dbname,
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
        autocommit=False,
    ) as conexion:
        try:
            with conexion.cursor() as cur:
                cur.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
        except psycopg.errors.InsufficientPrivilege as error:
            if _MENSAJE_DE_NO_SER_DUENIO not in str(error):
                raise
            return False
        else:
            return True
        finally:
            conexion.rollback()


@pytest.mark.parametrize("tabla", sorted(TABLAS_DE_SOLO_AGREGAR))
def test_el_migrador_no_es_dueno_de_las_tablas_de_solo_agregar(
    contenedor: PostgresContainer,  # noqa: F811
    esquema: None,
    tabla: str,
) -> None:
    puede_quitar_force = _migrador_puede_quitar_el_force_rls(contenedor, tabla)
    assert not puede_quitar_force, (
        f"proptech_migrador puede NO FORCE ROW LEVEL SECURITY sobre {tabla}: es su dueño (DBA-1)"
    )


def test_funciones_de_triggers_protegidos_no_son_del_migrador(
    contenedor: PostgresContainer,  # noqa: F811
    esquema: None,
) -> None:
    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        dbname=contenedor.dbname,
        user=contenedor.username,
        password=contenedor.password,
    ) as conexion:
        funciones = conexion.execute(
            "SELECT c.relname, p.proname, pg_get_userbyid(p.proowner) "
            "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "JOIN pg_proc p ON p.oid=t.tgfoid "
            "WHERE n.nspname='public' AND c.relname = ANY(%s) AND NOT t.tgisinternal",
            (list(TABLAS_DE_SOLO_AGREGAR),),
        ).fetchall()
    assert funciones
    assert all(dueno != MIGRADOR_USER for _, _, dueno in funciones), funciones


def test_migrador_no_puede_reemplazar_funcion_protegida(
    contenedor: PostgresContainer,  # noqa: F811
    esquema: None,
) -> None:
    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        dbname=contenedor.dbname,
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
    ) as conexion:
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="must be owner") as error:
            conexion.execute(
                "CREATE OR REPLACE FUNCTION public.fn_cuenta_bloqueada() "
                "RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NULL; END $$"
            )
        assert error.value.sqlstate == "42501"
