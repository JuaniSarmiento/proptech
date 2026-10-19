"""Revisión final (19/10/2026), arreglo 8: `proptech_app` no debe poder
escribir `alembic_version`.

DBA (revisión final): los `ALTER DEFAULT PRIVILEGES` que `roles.antes()`
deja fijados le dan a la app `SELECT, INSERT, UPDATE, DELETE` sobre TODA
tabla nueva del migrador — incluida `alembic_version`, que el propio
Alembic crea la primera vez que corre `upgrade`. La exclusión de
`alembic_version` en `_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP` sólo evita el
`GRANT` explícito de `antes()`; no deshace el regalo de los DEFAULT
PRIVILEGES, el mismo defecto que D9/D16 ya resolvieron para `auditoria` y
`configuracion_versionada`. `despues()` ahora revoca todo sobre
`alembic_version` y deja sólo `SELECT` (la app sí la lee: ver
`test_unidad_edificio_inmutable.py`)."""

import sys

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from ..conftest import IMAGEN_POSTGRES_PARA_TESTS
from .test_catalogo_rls import (
    APP_PASSWORD,
    APP_USER,
    ARRANQUE_PASSWORD,
    ARRANQUE_USER,
    _alembic_env,
    _correr,
    _entorno_de_roles,
)

pytestmark = pytest.mark.integracion


def test_proptech_app_no_puede_escribir_alembic_version_ni_tras_un_segundo_arranque() -> None:
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as contenedor:
        entorno = _entorno_de_roles(contenedor)
        roles = [sys.executable, "-m", "proptech_core.compartido.roles"]

        _correr([*roles, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
        _correr([*roles, "despues"], entorno)

        # Segundo arranque completo (idempotencia, D2): no tiene que
        # reabrir el permiso que el primer despues() ya cerró — alembic
        # upgrade no vuelve a CREATE TABLE alembic_version (ya existe), así
        # que los DEFAULT PRIVILEGES no se disparan de nuevo, pero antes()
        # sí vuelve a correr su GRANT amplio sobre el resto de las tablas.
        _correr([*roles, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
        _correr([*roles, "despues"], entorno)

        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=APP_USER,
            password=APP_PASSWORD,
            autocommit=True,
        ) as app:
            # La app sigue pudiendo LEER (lo necesita, D2/D7: confirmar que
            # las migraciones corrieron).
            assert app.execute("SELECT version_num FROM alembic_version").fetchone() is not None
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
                app.execute("UPDATE alembic_version SET version_num = version_num")
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
                app.execute("INSERT INTO alembic_version (version_num) VALUES ('no_deberia_poder')")
