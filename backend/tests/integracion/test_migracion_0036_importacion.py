"""Tarea 1.4 de `importacion-desde-excel`: la migración `0036_importacion` (design D5, D10).

L-082: el test prueba **su** migración (`downgrade 0035` / `upgrade 0036`), nunca "la última".
La tabla es mutable por la app (el borrador cambia de estado): no es de sólo agregar y no entra en
`TABLAS_DE_SOLO_AGREGAR`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

import psycopg
import pytest

from ._edificios import BaseDeEdificio, fijar_tenant
from ._importacion import Mundo, sembrar

pytestmark = pytest.mark.integracion

_VERSIONES = Path(__file__).resolve().parents[2] / "migraciones" / "versions"
_HUELLA = "a" * 64


def _filas(base: BaseDeEdificio, consulta: str, *parametros: object) -> list[tuple[object, ...]]:
    with base.conectar_app() as c:
        return [tuple(f) for f in c.execute(consulta, parametros).fetchall()]


def test_la_migracion_es_la_0036_sobre_la_0035() -> None:
    archivos = list(_VERSIONES.glob("0036_*.py"))
    assert len(archivos) == 1, "falta la migración 0036 (importacion)"
    texto = archivos[0].read_text()
    assert 'revision: str = "0036"' in texto
    assert 'down_revision: str | None = "0035"' in texto


def test_columnas_de_importacion(base_del_edificio: BaseDeEdificio) -> None:
    columnas = _filas(
        base_del_edificio,
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'importacion' ORDER BY column_name",
    )
    assert columnas == [
        ("administracion_id", "uuid", "NO"),
        ("archivo", "text", "NO"),
        ("complejo_id", "uuid", "NO"),
        ("creada_en", "timestamp with time zone", "NO"),
        ("creada_por", "uuid", "NO"),
        ("estado", "text", "NO"),
        ("fecha_de_migracion", "date", "NO"),
        ("huella", "text", "NO"),
        ("id", "uuid", "NO"),
    ]


def test_rls_forzada_con_su_politica_y_permisos_de_la_app(
    base_del_edificio: BaseDeEdificio,
) -> None:
    assert _filas(
        base_del_edificio,
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'importacion'",
    ) == [(True, True)]
    assert _filas(
        base_del_edificio,
        "SELECT policyname FROM pg_policies WHERE tablename = 'importacion'",
    ) == [("importacion_por_administracion",)]
    assert _filas(
        base_del_edificio,
        "SELECT privilege_type FROM information_schema.role_table_grants "
        "WHERE table_name = 'importacion' AND grantee = 'proptech_app' ORDER BY 1",
    ) == [("DELETE",), ("INSERT",), ("SELECT",), ("UPDATE",)]


def test_no_es_de_solo_agregar() -> None:
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    assert "importacion" not in TABLAS_DE_SOLO_AGREGAR


def test_las_claves_foraneas_son_compuestas_con_la_administracion(
    base_del_edificio: BaseDeEdificio,
) -> None:
    filas = _filas(
        base_del_edificio,
        "SELECT conname, confrelid::regclass::text, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'importacion'::regclass AND contype = 'f' ORDER BY conname",
    )
    assert [(f[0], f[1]) for f in filas] == [
        ("fk_importacion_complejo", "complejo"),
        ("fk_importacion_persona", "persona"),
    ]
    assert all("administracion_id" in str(f[2]) for f in filas)


def test_la_accion_esta_en_el_vocabulario_de_auditoria(base_del_edificio: BaseDeEdificio) -> None:
    assert _filas(
        base_del_edificio,
        "SELECT nombre FROM accion_de_auditoria WHERE nombre = 'importar_padron_y_saldos'",
    ) == [("importar_padron_y_saldos",)]


def _insertar(
    c: psycopg.Connection,
    mundo: Mundo,
    *,
    huella: str = _HUELLA,
    estado: str = "borrador",
    complejo: UUID | None = None,
) -> None:
    c.execute(
        "INSERT INTO importacion (administracion_id, complejo_id, archivo, huella, "
        "fecha_de_migracion, estado, creada_por) VALUES (%s, %s, 'a.xlsx', %s, %s, %s, %s)",
        (
            mundo.admin,
            complejo or mundo.torre,
            huella,
            date(2026, 10, 15),
            estado,
            mundo.super_admin.persona_id,
        ),
    )


def _con_conexion(base: BaseDeEdificio) -> tuple[psycopg.Connection, Mundo]:
    mundo = sembrar(base)
    assert _filas(base, "SELECT to_regclass('public.importacion') IS NOT NULL") == [(True,)], (
        "falta la tabla importacion (0036)"
    )
    c = base.conectar_app()
    c.autocommit = False
    fijar_tenant(c, mundo.admin)
    return c, mundo


def test_un_solo_borrador_por_edificio(base_del_edificio: BaseDeEdificio) -> None:
    c, mundo = _con_conexion(base_del_edificio)
    with c:
        _insertar(c, mundo)
        with pytest.raises(psycopg.errors.UniqueViolation):
            with c.transaction():
                _insertar(c, mundo, huella="b" * 64)
        _insertar(c, mundo, huella="c" * 64, estado="descartada")
        _insertar(c, mundo, huella="d" * 64, estado="confirmada")
        c.rollback()


def test_la_huella_es_unica_por_edificio_salvo_descartada(
    base_del_edificio: BaseDeEdificio,
) -> None:
    c, mundo = _con_conexion(base_del_edificio)
    with c:
        _insertar(c, mundo, estado="confirmada")
        with pytest.raises(psycopg.errors.UniqueViolation):
            with c.transaction():
                _insertar(c, mundo, estado="descartada", huella=_HUELLA)
                _insertar(c, mundo, estado="borrador", huella=_HUELLA)
        _insertar(c, mundo, estado="descartada", huella=_HUELLA)
        _insertar(c, mundo, estado="borrador", huella=_HUELLA, complejo=mundo.otro)
        c.rollback()


@pytest.mark.parametrize(
    ("huella", "estado"),
    [("corta", "borrador"), ("A" * 64, "borrador"), ("z" * 64, "borrador"), (_HUELLA, "rota")],
)
def test_la_huella_y_el_estado_tienen_vocabulario_cerrado(
    base_del_edificio: BaseDeEdificio, huella: str, estado: str
) -> None:
    c, mundo = _con_conexion(base_del_edificio)
    with c, pytest.raises(psycopg.errors.CheckViolation):
        _insertar(c, mundo, huella=huella, estado=estado)


def test_el_edificio_de_otra_administracion_se_rechaza_por_clave_foranea(
    base_del_edificio: BaseDeEdificio,
) -> None:
    c, mundo = _con_conexion(base_del_edificio)
    with c, pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insertar(c, mundo, complejo=mundo.complejo_b)


def test_baja_y_sube_conservando_el_vocabulario(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio

    def version() -> tuple[object, ...]:
        with base.conectar_migrador() as c:
            fila = c.execute("SELECT version_num FROM alembic_version").fetchone()
            return tuple(fila or ())

    def vocabulario() -> list[tuple[object, ...]]:
        with base.conectar_migrador() as c:
            return c.execute(
                "SELECT nombre FROM accion_de_auditoria WHERE nombre = 'importar_padron_y_saldos'"
            ).fetchall()

    assert vocabulario() == [("importar_padron_y_saldos",)]
    base.devolver_tablas_protegidas()  # la 0037 baja antes y su aceptación es de sólo agregar
    base.migrar("downgrade", "0035")
    assert version() == ("0035",)
    assert vocabulario() == []
    with base.conectar_migrador() as c:
        assert c.execute("SELECT to_regclass('public.importacion')").fetchone() == (None,)
    base.migrar("upgrade", "0036")
    assert version() == ("0036",)
    assert vocabulario() == [("importar_padron_y_saldos",)]
    base.roles("despues")


def test_no_baja_con_filas(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    c, mundo = _con_conexion(base)
    with c:
        _insertar(c, mundo)
        c.commit()
    base.devolver_tablas_protegidas()  # la 0037 baja antes y su aceptación es de sólo agregar
    with pytest.raises(AssertionError, match="tiene filas"):
        base.migrar("downgrade", "0035")
    with base.conectar_app() as c2:
        c2.autocommit = False
        fijar_tenant(c2, mundo.admin)
        assert c2.execute("SELECT count(*) FROM importacion").fetchone() == (1,), (
            "el downgrade rechazado se llevó la fila"
        )
        assert c2.execute(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'importacion'"
        ).fetchone() == (True,), "el downgrade rechazado dejó la RLS sin forzar"
        c2.execute("DELETE FROM importacion WHERE administracion_id = %s", (mundo.admin,))
        c2.commit()
