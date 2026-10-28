"""Enmienda E11 (RE11-02, RE11-03): no alcanza con que la función de un
trigger protegido sea del arranque si algo que ELLA llama sigue siendo del
migrador, y una función de trigger en otro esquema tiene que fallar cerrado
en vez de quedar aceptada en silencio.

Cada test levanta su PROPIO contenedor (nunca el de sesión, L-006): el
ataque de RE11-02 necesita intervenir como `proptech_migrador` ANTES de que
`despues()` corra por primera vez (la única ventana en la que el migrador
todavía es dueño de la función del trigger recién creada por la migración),
así que no puede reusar el fixture `esquema` de otro módulo, que ya corrió
`despues()` para dejar el escenario "ya protegido" a los demás tests.
"""

import subprocess
import sys

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from .test_catalogo_rls import (
    ARRANQUE_PASSWORD,
    ARRANQUE_USER,
    MIGRADOR_PASSWORD,
    MIGRADOR_USER,
    RAIZ_BACKEND,
    _alembic_env,
    _correr,
    _entorno_de_roles,
)

pytestmark = pytest.mark.integracion


def _contenedor_propio() -> PostgresContainer:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    return PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    )


def _conectar(contenedor: PostgresContainer, usuario: str, password: str) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        dbname=contenedor.dbname,
        user=usuario,
        password=password,
        autocommit=True,
    )


def test_dependencia_auxiliar_de_funcion_protegida_tambien_queda_del_arranque() -> None:
    """RE11-02: el migrador, mientras TODAVÍA es dueño de `fn_cuenta_bloqueada`
    (recién creada por la migración, antes del primer `despues()`), la
    reemplaza para que delegue en una auxiliar propia. `despues()` tiene que
    llevarse la auxiliar al arranque junto con la función: si no, el
    migrador podría, DESPUÉS de que `despues()` terminara bien, cambiar sólo
    la auxiliar y desactivar el bloqueo sin tocar la función protegida para
    nada."""
    roles_cmd = [sys.executable, "-m", "proptech_core.compartido.roles"]
    with _contenedor_propio() as contenedor:
        entorno = _entorno_de_roles(contenedor)
        _correr([*roles_cmd, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))

        # El migrador todavía es dueño de fn_cuenta_bloqueada (la creó la
        # migración 0023, `despues()` nunca corrió todavía): simula lo que
        # haría una migración futura, delegando el bloqueo en una auxiliar.
        with _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD) as migrador:
            migrador.execute(
                "CREATE FUNCTION public.fn_cuenta_bloqueada_aux_re11() RETURNS boolean "
                "LANGUAGE sql AS $$ SELECT true $$"
            )
            migrador.execute(
                "CREATE OR REPLACE FUNCTION public.fn_cuenta_bloqueada() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN "
                "IF public.fn_cuenta_bloqueada_aux_re11() THEN "
                "RAISE EXCEPTION 'cuenta no admite %', TG_OP; "
                "END IF; RETURN NULL; END $$"
            )

        _correr([*roles_cmd, "despues"], entorno)

        with _conectar(contenedor, contenedor.username, contenedor.password) as arranque:
            duenos: dict[str, str] = dict(
                arranque.execute(
                    "SELECT proname, pg_get_userbyid(proowner) FROM pg_proc "
                    "WHERE proname IN ('fn_cuenta_bloqueada', 'fn_cuenta_bloqueada_aux_re11') "
                    "AND pronamespace = 'public'::regnamespace"
                ).fetchall()
            )
        assert duenos.get("fn_cuenta_bloqueada") == contenedor.username, duenos
        assert duenos.get("fn_cuenta_bloqueada_aux_re11") == contenedor.username, (
            f"la auxiliar sigue sin ser del arranque: {duenos} (RE11-02)"
        )

        # El migrador no puede reemplazar NI la función protegida NI su auxiliar.
        with _conectar(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD) as migrador:
            with pytest.raises(
                psycopg.errors.InsufficientPrivilege, match="must be owner"
            ) as error:
                migrador.execute(
                    "CREATE OR REPLACE FUNCTION public.fn_cuenta_bloqueada_aux_re11() "
                    "RETURNS boolean LANGUAGE sql AS $$ SELECT false $$"
                )
            assert error.value.sqlstate == "42501"
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="must be owner"):
                migrador.execute(
                    "CREATE OR REPLACE FUNCTION public.fn_cuenta_bloqueada() RETURNS trigger "
                    "LANGUAGE plpgsql AS $$ BEGIN RETURN NULL; END $$"
                )

        # El bloqueo por sentencia sigue firme después de `despues()`: ni el
        # propio rol de arranque (superusuario) lo evita, porque los
        # triggers corren para cualquier rol.
        with _conectar(contenedor, contenedor.username, contenedor.password) as arranque:
            with pytest.raises(psycopg.errors.RaiseException, match="cuenta no admite"):
                arranque.execute("UPDATE cuenta SET id = id WHERE false")


def test_funcion_de_trigger_protegido_en_otro_esquema_falla_cerrado() -> None:
    """RE11-03: una función de trigger que vive en OTRO esquema (no
    `public`) hace que `despues()` falle con un error claro y cerrado
    (`function public.<nombre>() does not exist`), nunca que la acepte en
    silencio como si no tuviera dueño que verificar."""
    roles_cmd = [sys.executable, "-m", "proptech_core.compartido.roles"]
    with _contenedor_propio() as contenedor:
        entorno = _entorno_de_roles(contenedor)
        _correr([*roles_cmd, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))

        with _conectar(contenedor, contenedor.username, contenedor.password) as arranque:
            arranque.execute("CREATE SCHEMA re11_otro_esquema")
            arranque.execute(
                "CREATE FUNCTION re11_otro_esquema.aux() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RETURN NULL; END $$"
            )
            arranque.execute(
                "CREATE TRIGGER trg_re11_otro_esquema BEFORE INSERT ON cuenta "
                "FOR EACH ROW EXECUTE FUNCTION re11_otro_esquema.aux()"
            )
        try:
            resultado = subprocess.run(
                [*roles_cmd, "despues"],
                cwd=RAIZ_BACKEND,
                env=entorno,
                capture_output=True,
                text=True,
            )
            assert resultado.returncode != 0, (
                "despues() tenía que fallar con la función de otro esquema (RE11-03)"
            )
            assert "public.aux" in resultado.stderr or "does not exist" in resultado.stderr, (
                resultado.stderr
            )
        finally:
            with _conectar(contenedor, contenedor.username, contenedor.password) as arranque:
                arranque.execute("DROP TRIGGER IF EXISTS trg_re11_otro_esquema ON cuenta")
                arranque.execute("DROP SCHEMA IF EXISTS re11_otro_esquema CASCADE")
