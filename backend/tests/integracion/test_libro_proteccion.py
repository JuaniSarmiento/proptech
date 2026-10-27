"""Protección del libro por privilegios, triggers y propiedad (1.1 a 1.3)."""

from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from psycopg import errors, sql

from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

from ._edificios import BaseDeEdificio
from ._libro import LIBRO, insertar, sembrar_libro
from .test_libro_esquema import libro as _fixture_libro  # noqa: F401
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


def operaciones(tabla: str) -> dict[str, sql.Composed]:
    plantillas = {
        "UPDATE": "UPDATE {tabla} SET id=id WHERE false",
        "DELETE": "DELETE FROM {tabla} WHERE false",
        "TRUNCATE": "TRUNCATE {tabla} CASCADE",
        "UPSERT": "INSERT INTO {tabla} OVERRIDING SYSTEM VALUE SELECT * FROM {tabla} "
        "WHERE false ON CONFLICT(id) DO UPDATE SET id=EXCLUDED.id",
    }
    return {
        nombre: sql.SQL(consulta).format(tabla=sql.Identifier(tabla))
        for nombre, consulta in plantillas.items()
    }


def test_lista_declara_las_seis_y_no_el_candado() -> None:
    assert set(LIBRO) <= set(TABLAS_DE_SOLO_AGREGAR)
    assert "candado_de_cuenta" not in TABLAS_DE_SOLO_AGREGAR
    for tabla in LIBRO:
        assert TABLAS_DE_SOLO_AGREGAR[tabla].mensaje == f"{tabla} no admite"
        assert TABLAS_DE_SOLO_AGREGAR[tabla].triggers == frozenset(
            {
                f"trg_{tabla}_sin_update_delete",
                f"trg_{tabla}_sin_truncate",
                f"trg_{tabla}_sin_update_delete_por_sentencia",
            }
        )


@pytest.mark.parametrize("tabla", LIBRO)
@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE", "TRUNCATE", "UPSERT"])
def test_app_sin_permisos_de_edicion(
    base_del_edificio: BaseDeEdificio, tabla: str, operacion: str
) -> None:
    with base_del_edificio.conectar_app() as c:
        with pytest.raises(errors.InsufficientPrivilege) as e, c.transaction():
            c.execute(operaciones(tabla)[operacion])
        assert e.value.sqlstate == "42501"


@pytest.mark.parametrize("tabla", LIBRO)
@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE", "TRUNCATE", "UPSERT"])
def test_trigger_por_sentencia(
    base_del_edificio: BaseDeEdificio, tabla: str, operacion: str
) -> None:
    with arranque(base_del_edificio) as c:
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(operaciones(tabla)[operacion])
        assert e.value.sqlstate == "P0001"
        assert (
            e.value.diag.message_primary
            == f"{tabla} no admite {'UPDATE' if operacion == 'UPSERT' else operacion}"
        )


@pytest.mark.parametrize("tabla", LIBRO)
def test_duenios_y_references(base_del_edificio: BaseDeEdificio, tabla: str) -> None:
    base = base_del_edificio
    with arranque(base) as c:
        assert c.execute(
            "SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename=%s", (tabla,)
        ).fetchone() == (base.contenedor.username,)
        assert c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid=to_regprocedure(%s)",
            (f"fn_{tabla}_bloqueada()",),
        ).fetchone() == (base.contenedor.username,)
    with base.conectar_migrador() as c:
        nombre = f"sonda_fk_{tabla}"
        try:
            admitida = True
            try:
                c.execute(
                    sql.SQL("CREATE TABLE {} (id uuid REFERENCES {}(id))").format(
                        sql.Identifier(nombre), sql.Identifier(tabla)
                    )
                )
            except errors.InsufficientPrivilege:
                admitida = False
            assert admitida, f"REFERENCES faltante sobre {tabla}"
            with pytest.raises(errors.ForeignKeyViolation) as e, c.transaction():
                insertar(c, nombre, {"id": uuid4()})
            assert e.value.sqlstate == "23503"
        finally:
            c.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(nombre)))


@pytest.mark.parametrize("tabla", LIBRO)
@pytest.mark.parametrize("operacion", ["ALTER", "CREATE INDEX", "DROP INDEX", "INSERT"])
def test_references_no_da_propiedad(
    base_del_edificio: BaseDeEdificio, tabla: str, operacion: str
) -> None:
    base = base_del_edificio
    indice = f"sonda_indice_{tabla}"
    with arranque(base) as dueno, base.conectar_migrador() as c:
        if operacion == "DROP INDEX":
            dueno.execute(
                sql.SQL("CREATE INDEX {} ON {} (id)").format(
                    sql.Identifier(indice), sql.Identifier(tabla)
                )
            )
        sentencias: dict[str, str | sql.Composed] = {
            "ALTER": f"ALTER TABLE {tabla} ADD COLUMN prohibida int",
            "CREATE INDEX": f"CREATE INDEX {indice} ON {tabla}(id)",
            "DROP INDEX": f"DROP INDEX {indice}",
            "INSERT": sql.SQL(
                "INSERT INTO {tabla} OVERRIDING SYSTEM VALUE SELECT * FROM {tabla} WHERE false"
            ).format(tabla=sql.Identifier(tabla)),
        }
        try:
            with pytest.raises(errors.InsufficientPrivilege) as e, c.transaction():
                c.execute(sentencias[operacion])
            assert e.value.sqlstate == "42501"
        finally:
            # F1-11: si un CREATE INDEX pasara, la sonda no queda viva para el caso siguiente.
            dueno.execute(sql.SQL("DROP INDEX IF EXISTS {}").format(sql.Identifier(indice)))


def test_revocar_references_conserva_fk(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    with arranque(base) as dueno, base.conectar_migrador() as c:
        c.execute("CREATE TABLE sonda_anterior (id uuid REFERENCES movimiento(id))")
        try:
            dueno.execute("REVOKE REFERENCES ON movimiento FROM proptech_migrador")
            assert c.execute(
                "SELECT count(*) FROM pg_constraint WHERE conrelid='sonda_anterior"
                "'::regclass AND contype='f'"
            ).fetchone() == (1,)
            with pytest.raises(errors.ForeignKeyViolation), c.transaction():
                c.execute("INSERT INTO sonda_anterior VALUES (%s)", (uuid4(),))
            with pytest.raises(errors.InsufficientPrivilege) as e, c.transaction():
                c.execute("CREATE TABLE sonda_nueva (id uuid REFERENCES movimiento(id))")
            assert e.value.sqlstate == "42501"
        finally:
            dueno.execute("GRANT REFERENCES ON movimiento TO proptech_migrador")
            c.execute("DROP TABLE IF EXISTS sonda_nueva")
            c.execute("DROP TABLE sonda_anterior")


def test_vocabulario_solo_select_y_ciclo_repetido(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    for vuelta in range(2):
        if vuelta:
            base.roles("antes")
            base.migrar("upgrade", "head")
            base.roles("despues")
        with base.conectar_app() as c:
            assert c.execute("SELECT count(*) FROM tipo_de_movimiento").fetchone() == (14,)
            for consulta in (
                "INSERT INTO tipo_de_movimiento VALUES ('prohibido','credito')",
                "UPDATE tipo_de_movimiento SET tipo=tipo WHERE false",
                "DELETE FROM tipo_de_movimiento WHERE false",
            ):
                with pytest.raises(errors.InsufficientPrivilege) as e, c.transaction():
                    c.execute(consulta)
                assert e.value.sqlstate == "42501"
    with base.conectar_migrador() as c, c.transaction(force_rollback=True):
        c.execute("INSERT INTO tipo_de_movimiento VALUES ('futuro','credito')")
        assert c.execute("SELECT tipo FROM tipo_de_movimiento WHERE tipo='futuro'").fetchone() == (
            "futuro",
        )


def test_candado_permite_update_y_lock_pero_no_delete(libro: Any) -> None:
    c = libro.conexion
    c.execute(
        "INSERT INTO candado_de_cuenta (cuenta_id,administracion_id) VALUES (%s,%s)",
        (libro.cuenta, libro.admin),
    )
    assert c.execute("SELECT cuenta_id FROM candado_de_cuenta FOR UPDATE").fetchone() == (
        libro.cuenta,
    )
    assert c.execute("UPDATE candado_de_cuenta SET cuenta_id=cuenta_id").rowcount == 1
    with pytest.raises(errors.InsufficientPrivilege) as e, c.transaction():
        c.execute("DELETE FROM candado_de_cuenta WHERE false")
    assert e.value.sqlstate == "42501"


@pytest.mark.parametrize("tabla", LIBRO)
@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE"])
def test_trigger_por_fila_sin_el_de_sentencia(
    base_del_edificio: BaseDeEdificio, tabla: str, operacion: str
) -> None:
    # Todo en una transacción del arranque revertida: DDL y GRANT explícitos antes de SET ROLE.
    with arranque(base_del_edificio) as c, c.transaction(force_rollback=True):
        c.execute(
            sql.SQL("ALTER TABLE {} DISABLE TRIGGER {}").format(
                sql.Identifier(tabla),
                sql.Identifier(f"trg_{tabla}_sin_update_delete_por_sentencia"),
            )
        )
        c.execute(
            sql.SQL("GRANT UPDATE, DELETE ON {} TO proptech_app").format(sql.Identifier(tabla))
        )
        c.execute("SET LOCAL ROLE proptech_app")
        datos = sembrar_libro(c)
        # Una fila sin hijas (F1-02): el DELETE no choca con ninguna FK, así que el único que
        # puede frenarlo es el trigger por fila.
        extra: dict[str, dict[str, Any]] = {"emision": {"periodo": date(2026, 11, 1)}}
        nueva = datos.agregar(tabla, **extra.get(tabla, {}))
        sentencia = sql.SQL(
            "UPDATE {} SET id=id WHERE id=%s"
            if operacion == "UPDATE"
            else "DELETE FROM {} WHERE id=%s"
        ).format(sql.Identifier(tabla))
        with pytest.raises(errors.RaiseException) as e, c.transaction():
            c.execute(sentencia, (nueva["id"],))
        assert e.value.sqlstate == "P0001"
        assert (
            e.value.diag.message_primary
            == f"{tabla} no admite {'UPDATE' if operacion == 'UPSERT' else operacion}"
        )


def test_base_reproduce_dueno_del_deploy(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    with arranque(base) as c:
        assert c.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()"
        ).fetchone() == (base.contenedor.username,)
        assert c.execute(
            "SELECT pg_has_role('proptech_migrador', nspowner, 'MEMBER') FROM "
            "pg_namespace WHERE nspname='public'"
        ).fetchone() == (False,)
        assert c.execute(
            "SELECT pg_has_role('proptech_app', nspowner, 'MEMBER') FROM pg_na"
            "mespace WHERE nspname='public'"
        ).fetchone() == (False,)


@pytest.mark.parametrize("orden", ["homonima_antes", "public_antes", "solo_homonima"])
def test_homonima_no_oculta_public(base_del_edificio: BaseDeEdificio, orden: str) -> None:
    """RB-4 por el efecto (F1-05): una `movimiento` del superusuario en otro esquema no hace
    pasar el chequeo. `solo_homonima` no depende del orden físico del catálogo: sin el filtro
    `schemaname='public'`, la homónima protegida ocupa el lugar de la que falta en public."""
    from sqlalchemy import create_engine

    from proptech_core.compartido.base_de_datos import (
        TablasDeSoloAgregarDesprotegidas,
        verificar_tablas_de_solo_agregar,
    )

    base = base_del_edificio
    with arranque(base) as c:
        c.execute("ALTER TABLE public.movimiento RENAME TO movimiento_original")
        c.execute("CREATE SCHEMA otro_libro")
        public = "CREATE TABLE public.movimiento (id uuid)"
        otro = "CREATE TABLE otro_libro.movimiento (id uuid)"
        sentencias = {
            "homonima_antes": [otro, public],
            "public_antes": [public, otro],
            "solo_homonima": [otro],
        }[orden]
        for sentencia in sentencias:
            c.execute(sentencia)
        if public in sentencias:
            c.execute("ALTER TABLE public.movimiento OWNER TO proptech_migrador")
    engine = create_engine("postgresql+psycopg://", creator=base.conectar_app)
    try:
        with pytest.raises(TablasDeSoloAgregarDesprotegidas, match="movimiento"):
            verificar_tablas_de_solo_agregar(engine)
    finally:
        engine.dispose()
        with arranque(base) as c:
            c.execute("DROP TABLE IF EXISTS public.movimiento")
            c.execute("DROP SCHEMA otro_libro CASCADE")
            c.execute("ALTER TABLE public.movimiento_original RENAME TO movimiento")


@pytest.mark.parametrize(
    "tabla,mensaje",
    [("movimiento", "otra_tabla no admite"), ("emision", "evento_de_emision no admite")],
)
def test_despues_detecta_funcion_con_texto_ajeno(
    base_del_edificio: BaseDeEdificio, tabla: str, mensaje: str
) -> None:
    base = base_del_edificio
    with arranque(base) as c:
        fila_funcion = c.execute(
            "SELECT pg_get_functiondef(to_regprocedure(%s))", (f"fn_{tabla}_bloqueada()",)
        ).fetchone()
        assert fila_funcion is not None
        definicion = fila_funcion[0]
        c.execute(
            sql.SQL(
                "CREATE OR REPLACE FUNCTION {}() RETURNS trigger LANGUAGE plpgsql "
                "AS $$ BEGIN RAISE EXCEPTION {},TG_OP; END $$"
            ).format(sql.Identifier(f"fn_{tabla}_bloqueada"), sql.Literal(mensaje + " %"))
        )
    try:
        with pytest.raises(AssertionError, match=f"la protección de {tabla} no se pudo confirmar"):
            base.roles("despues")
    finally:
        with arranque(base) as c:
            c.execute(definicion)
        base.roles("despues")


def test_despues_detecta_funcion_de_otro_dueno(
    base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proptech_core.compartido import roles
    from proptech_core.compartido.configuracion import ConfiguracionDeArranque

    base = base_del_edificio
    entorno = {
        **base.entorno,
        "POSTGRES_USER": base.contenedor.username,
        "POSTGRES_PASSWORD": base.contenedor.password,
        "POSTGRES_APP_USER": "proptech_app",
        "POSTGRES_APP_PASSWORD": "clave-app-de-sesion-no-real",
        "POSTGRES_RESPALDO_USER": "proptech_respaldo",
        "POSTGRES_RESPALDO_PASSWORD": "clave-respaldo-de-sesion-no-real",
    }
    for k, v in entorno.items():
        monkeypatch.setenv(k, v)
    verificar = roles._verificar_tabla_protegida

    def corromper_y_verificar(cur: Any, tabla: str, declaracion: Any, dueno: str) -> None:
        if tabla == "movimiento":
            cur.execute("ALTER FUNCTION fn_movimiento_bloqueada() OWNER TO proptech_migrador")
        verificar(cur, tabla, declaracion, dueno)

    monkeypatch.setattr(roles, "_verificar_tabla_protegida", corromper_y_verificar)
    with pytest.raises(roles.AuditoriaNoProtegida, match="función con otro dueño"):
        roles.despues(ConfiguracionDeArranque())
    # despues revierte también la avería inyectada entre transferencia y sonda.
    with arranque(base) as c:
        assert c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid='fn_movim"
            "iento_bloqueada()'::regprocedure"
        ).fetchone() == (base.contenedor.username,)


@pytest.mark.parametrize("tabla", (*LIBRO, "candado_de_cuenta"))
def test_rls_habilitada_y_forzada(base_del_edificio: BaseDeEdificio, tabla: str) -> None:
    with base_del_edificio.conectar_app() as c:
        assert c.execute(
            "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=to_regclass(%s)",
            (f"public.{tabla}",),
        ).fetchone() == (True, True)


def test_candado_aislado_por_administracion(libro: Any) -> None:
    """F1-12: la política del candado existe y filtra por el efecto, no sólo por las banderas."""
    from ._edificios import fijar_tenant

    c = libro.conexion
    c.execute(
        "INSERT INTO candado_de_cuenta (cuenta_id,administracion_id) VALUES (%s,%s)",
        (libro.cuenta, libro.admin),
    )
    assert c.execute("SELECT count(*) FROM candado_de_cuenta").fetchone() == (1,)
    fijar_tenant(c, libro.edificios.administracion_b)
    assert c.execute("SELECT count(*) FROM candado_de_cuenta").fetchone() == (0,)
    with pytest.raises(errors.InsufficientPrivilege) as e, c.transaction():
        c.execute(
            "INSERT INTO candado_de_cuenta (cuenta_id,administracion_id) VALUES (%s,%s)",
            (libro.cuenta, libro.admin),
        )
    assert e.value.sqlstate == "42501"
