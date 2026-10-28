"""E11 (el motivo original) y su enmienda: el caso de restauración.

`pg_restore --no-owner` deja TODOS los objetos restaurados a nombre de quien
restaura (el rol de arranque), y la migración `0027` hace
`CREATE OR REPLACE FUNCTION fn_grupo_generales_protegido()` conectada como
el migrador — ésa es la falla original de E11 ("must be owner of
function"). La función vive en un trigger de `grupo_de_reparto`, que NO es
una tabla de `TABLAS_DE_SOLO_AGREGAR`: la enmienda (RE11-01/02) tiene que
seguir devolviéndosela al migrador en `roles antes`, nunca dejarla del
arranque como a las protegidas.

Contenedor propio (L-006). `pg_dump`/`pg_restore`/`dropdb`/`createdb`
corren DENTRO del contenedor (`contenedor.exec`, mismos binarios que trae
la imagen oficial de Postgres): así el ensayo no depende de tener esos
clientes instalados en el host que corre los tests.
"""

import sys

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from .test_catalogo_rls import (
    ARRANQUE_PASSWORD,
    ARRANQUE_USER,
    MIGRADOR_USER,
    _alembic_env,
    _correr,
    _entorno_de_roles,
)

pytestmark = pytest.mark.integracion

# Ruta DENTRO del contenedor descartable (`contenedor.exec`), nunca en el
# host que corre los tests: el riesgo de ruta predecible que S108 señala no
# aplica acá, el contenedor se destruye entero al salir del `with`.
_ARCHIVO_DE_RESPALDO = "/tmp/e11_respaldo.dump"  # noqa: S108


def test_restaurar_antes_de_0027_deja_que_antes_reasigne_fn_grupo_generales_protegido() -> None:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    roles_cmd = [sys.executable, "-m", "proptech_core.compartido.roles"]
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as contenedor:
        entorno = _entorno_de_roles(contenedor)

        # Deploy real hasta justo ANTES de 0027 (D9 del 4a: `despues()`
        # está pensado para la cabeza de Alembic, no para una revisión
        # intermedia -- por eso acá no se corre).
        _correr([*roles_cmd, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "0026"], _alembic_env(contenedor))

        volcado = contenedor.exec(
            [
                "pg_dump",
                "-U",
                contenedor.username,
                "-Fc",
                "-f",
                _ARCHIVO_DE_RESPALDO,
                contenedor.dbname,
            ]
        )
        assert volcado.exit_code == 0, volcado.output.decode()

        # Simula la restauración operativa (D9): la base se recrea vacía y
        # se restaura con `--no-owner` -- todo objeto queda del rol que
        # restaura, el de arranque, exactamente como en un restore real.
        tira_la_base = contenedor.exec(["dropdb", "-U", contenedor.username, contenedor.dbname])
        assert tira_la_base.exit_code == 0, tira_la_base.output.decode()
        crea_la_base = contenedor.exec(["createdb", "-U", contenedor.username, contenedor.dbname])
        assert crea_la_base.exit_code == 0, crea_la_base.output.decode()
        restaura = contenedor.exec(
            [
                "pg_restore",
                "-U",
                contenedor.username,
                "--no-owner",
                "--no-acl",
                "-d",
                contenedor.dbname,
                _ARCHIVO_DE_RESPALDO,
            ]
        )
        assert restaura.exit_code == 0, restaura.output.decode()

        # Confirma la falla original de E11: después del restore, la
        # función queda del rol de arranque -- el migrador ya no es su
        # dueño, y 0027 corre conectada como el migrador.
        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=contenedor.username,
            password=contenedor.password,
            autocommit=True,
        ) as conexion:
            dueno_tras_restore = conexion.execute(
                "SELECT pg_get_userbyid(proowner) FROM pg_proc "
                "WHERE proname = 'fn_grupo_generales_protegido' "
                "AND pronamespace = 'public'::regnamespace"
            ).fetchone()
        assert dueno_tras_restore is not None
        assert dueno_tras_restore[0] == contenedor.username, (
            "la función debía quedar del arranque tras el restore (si no, "
            "este test ya no reproduce la falla original de E11)"
        )

        # `roles antes` (enmienda E11): fn_grupo_generales_protegido NO es
        # trigger de una tabla de TABLAS_DE_SOLO_AGREGAR -- tiene que
        # volver al migrador, igual que antes de la enmienda.
        _correr([*roles_cmd, "antes"], entorno)

        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=contenedor.username,
            password=contenedor.password,
            autocommit=True,
        ) as conexion:
            dueno_tras_antes = conexion.execute(
                "SELECT pg_get_userbyid(proowner) FROM pg_proc "
                "WHERE proname = 'fn_grupo_generales_protegido' "
                "AND pronamespace = 'public'::regnamespace"
            ).fetchone()
        assert dueno_tras_antes is not None
        assert dueno_tras_antes[0] == MIGRADOR_USER, (
            f"fn_grupo_generales_protegido no volvió al migrador tras `antes` "
            f"(es {dueno_tras_antes[0]!r}): 0027 va a fallar con 'must be owner'"
        )

        # El caso que motivó E11: con la función ya del migrador, 0027
        # (CREATE OR REPLACE conectada como el migrador) y `despues()`
        # tienen que terminar en 0, sin "must be owner of function".
        _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
        _correr([*roles_cmd, "despues"], entorno)
