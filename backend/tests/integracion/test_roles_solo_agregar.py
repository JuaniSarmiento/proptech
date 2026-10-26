"""D16: dos arranques no restituyen UPDATE/DELETE a una tabla de sólo agregar.

La tabla de prueba reemplaza a la futura configuración en un contenedor propio;
se migra hasta 0008 y se declara la forma exigida por D2 (triggers y RLS),
para seguir probando la capa independiente de GRANT con los triggers apagados.
"""

import sys
from uuid import uuid4

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
    _conectar_como_migrador,
    _correr,
    _entorno_de_roles,
)

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE"])
def test_dos_up_con_trigger_desactivado_conservan_la_capa_de_permisos(operacion: str) -> None:
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as contenedor:
        entorno = _entorno_de_roles(contenedor)
        roles = [sys.executable, "-m", "proptech_core.compartido.roles"]
        _correr([*roles, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "0008"], _alembic_env(contenedor))
        admin = uuid4()
        with _conectar_como_migrador(contenedor) as migrador:
            migrador.execute(
                "CREATE TABLE configuracion_versionada (administracion_id uuid, valor int)"
            )
            migrador.execute("INSERT INTO configuracion_versionada VALUES (%s, 1)", (admin,))
            migrador.execute(
                "CREATE FUNCTION fn_copia() RETURNS trigger LANGUAGE plpgsql "
                "AS $$ BEGIN RAISE EXCEPTION 'configuracion_versionada no admite cambios'; END $$"
            )
            migrador.execute(
                "CREATE TRIGGER trg_configuracion_sin_update_delete "
                "BEFORE UPDATE OR DELETE ON configuracion_versionada "
                "FOR EACH ROW EXECUTE FUNCTION fn_copia()"
            )
            migrador.execute(
                "CREATE TRIGGER trg_configuracion_sin_truncate BEFORE TRUNCATE "
                "ON configuracion_versionada FOR EACH STATEMENT EXECUTE FUNCTION fn_copia()"
            )
            migrador.execute(
                "CREATE TRIGGER trg_configuracion_sin_update_delete_por_sentencia "
                "BEFORE UPDATE OR DELETE ON configuracion_versionada "
                "FOR EACH STATEMENT EXECUTE FUNCTION fn_copia()"
            )
            migrador.execute("ALTER TABLE configuracion_versionada ENABLE ROW LEVEL SECURITY")
            migrador.execute("ALTER TABLE configuracion_versionada FORCE ROW LEVEL SECURITY")
            migrador.execute(
                "CREATE POLICY sonda ON configuracion_versionada USING (true) WITH CHECK (true)"
            )
            migrador.execute(
                "REVOKE UPDATE, DELETE, TRUNCATE ON configuracion_versionada FROM proptech_app"
            )
        _correr([*roles, "despues"], entorno)
        _correr([*roles, "antes"], entorno)
        _correr(["uv", "run", "alembic", "upgrade", "0008"], _alembic_env(contenedor))
        _correr([*roles, "despues"], entorno)
        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=ARRANQUE_USER,
            password=ARRANQUE_PASSWORD,
            autocommit=True,
        ) as arranque:
            arranque.execute("ALTER TABLE configuracion_versionada DISABLE TRIGGER USER")
        with psycopg.connect(
            host=contenedor.get_container_host_ip(),
            port=contenedor.get_exposed_port(5432),
            dbname=contenedor.dbname,
            user=APP_USER,
            password=APP_PASSWORD,
            autocommit=True,
        ) as app:
            sentencia = (
                "UPDATE configuracion_versionada SET valor = 2"
                if operacion == "UPDATE"
                else "DELETE FROM configuracion_versionada"
            )
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
                app.execute(sentencia)
            assert app.execute("SELECT * FROM configuracion_versionada").fetchall() == [(admin, 1)]
