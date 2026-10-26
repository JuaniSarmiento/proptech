"""D2: cada rotura se aplica sobre Postgres y no confirma transferencias."""

import subprocess
import sys

import pytest

from proptech_core.compartido.roles import AuditoriaNoProtegida, _verificar_tabla_protegida
from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR, TablaProtegida

from ..conftest import (
    APP_PASSWORD_DE_SESION,
    APP_USER_DE_SESION,
    RESPALDO_PASSWORD_DE_SESION,
    RESPALDO_USER_DE_SESION,
)
from ._edificios import BaseDeEdificio
from .test_propiedad_protegida import devolver_configuracion
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize("rotura", ["trigger", "funcion", "rls", "otro_error", "texto_ajeno"])
def test_despues_rechaza_roturas_sin_confirmar(
    base_para_migraciones: BaseDeEdificio, rotura: str
) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "head")
    devolver_configuracion(base)
    with arranque(base) as c:
        fila_funcion = c.execute(
            "SELECT pg_get_functiondef('fn_configuracion_versionada_bloqueada()'::regprocedure)"
        ).fetchone()
        assert fila_funcion is not None
        definicion = fila_funcion[0]
        try:
            if rotura == "trigger":
                c.execute(
                    "ALTER TABLE configuracion_versionada DISABLE TRIGGER "
                    "trg_configuracion_sin_update_delete_por_sentencia"
                )
            elif rotura == "rls":
                c.execute("ALTER TABLE configuracion_versionada DISABLE ROW LEVEL SECURITY")
            else:
                cuerpo = (
                    "RETURN NULL;"
                    if rotura == "funcion"
                    else "IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'otro error' USING "
                    "ERRCODE='23514'; END IF; RAISE EXCEPTION "
                    "'configuracion_versionada no admite %',TG_OP;"
                    if rotura == "otro_error"
                    else "RAISE EXCEPTION 'auditoria no admite cambios';"
                )
                c.execute(
                    "CREATE OR REPLACE FUNCTION fn_configuracion_versionada_bloqueada() "
                    "RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN " + cuerpo + " END $$"
                )
            with pytest.raises(AssertionError, match="configuracion_versionada"):
                base.roles("despues")
            assert c.execute(
                "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND "
                "tablename='configuracion_versionada'"
            ).fetchone() == (base.entorno["POSTGRES_MIGRADOR_USER"],)
        finally:
            c.execute(definicion)
            c.execute(
                "ALTER TABLE configuracion_versionada ENABLE TRIGGER "
                "trg_configuracion_sin_update_delete_por_sentencia"
            )
            c.execute("ALTER TABLE configuracion_versionada ENABLE ROW LEVEL SECURITY")


def test_tabla_vacia_pasa_y_fk_entrante_no_pierde_filas(
    base_para_migraciones: BaseDeEdificio,
) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "head")
    base.roles("despues")
    with arranque(base) as c, c.transaction(force_rollback=True), c.cursor() as cur:
        assert c.execute("SELECT count(*) FROM configuracion_versionada").fetchone() == (0,)
        _verificar_tabla_protegida(
            cur,
            "configuracion_versionada",
            TABLAS_DE_SOLO_AGREGAR["configuracion_versionada"],
            base.contenedor.username,
        )
        cur.execute("CREATE TABLE sonda_padre (id int PRIMARY KEY)")
        cur.execute("CREATE TABLE sonda_hija (id int REFERENCES sonda_padre)")
        cur.execute("INSERT INTO sonda_padre VALUES (1)")
        cur.execute("INSERT INTO sonda_hija VALUES (1)")
        cur.execute("ALTER TABLE sonda_padre ENABLE ROW LEVEL SECURITY")
        cur.execute("ALTER TABLE sonda_padre FORCE ROW LEVEL SECURITY")
        cur.execute(
            "CREATE FUNCTION fn_sonda() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE "
            "EXCEPTION 'sonda_padre no admite %',TG_OP; END $$"
        )
        cur.execute(
            "CREATE TRIGGER bloqueo BEFORE UPDATE OR DELETE OR TRUNCATE ON sonda_padre FOR "
            "EACH STATEMENT EXECUTE FUNCTION fn_sonda()"
        )
        declaracion = TablaProtegida("sonda_padre no admite", frozenset({"bloqueo"}))
        _verificar_tabla_protegida(cur, "sonda_padre", declaracion, base.contenedor.username)
        assert c.execute("SELECT * FROM sonda_hija").fetchall() == [(1,)]
        cur.execute(
            "CREATE OR REPLACE FUNCTION fn_sonda() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN IF TG_OP='TRUNCATE' THEN RETURN NULL; END IF; RAISE EXCEPTION "
            "'sonda_padre no admite %', TG_OP; END $$"
        )
        with pytest.raises(AuditoriaNoProtegida, match=r"sonda_padre.*TRUNCATE"):
            _verificar_tabla_protegida(cur, "sonda_padre", declaracion, base.contenedor.username)
        assert c.execute("SELECT * FROM sonda_hija").fetchall() == [(1,)]


def test_tabla_ausente_se_dice(base_para_migraciones: BaseDeEdificio) -> None:
    base = base_para_migraciones
    base.migrar("upgrade", "head")
    with arranque(base) as c:
        c.execute("ALTER TABLE configuracion_versionada RENAME TO configuracion_apartada")
        try:
            entorno = {
                **base.entorno,
                "POSTGRES_USER": base.contenedor.username,
                "POSTGRES_PASSWORD": base.contenedor.password,
                "POSTGRES_APP_USER": APP_USER_DE_SESION,
                "POSTGRES_APP_PASSWORD": APP_PASSWORD_DE_SESION,
                "POSTGRES_RESPALDO_USER": RESPALDO_USER_DE_SESION,
                "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD_DE_SESION,
            }
            r = subprocess.run(
                [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
                env=entorno,
                capture_output=True,
                text=True,
            )
            assert r.returncode == 0, r.stderr
            assert "configuracion_versionada: no existe, se saltea" in r.stdout
        finally:
            c.execute("ALTER TABLE configuracion_apartada RENAME TO configuracion_versionada")
