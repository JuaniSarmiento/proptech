"""Tarea 2.2 de `importacion-desde-excel`: la `0037_borrador_de_saldos` baja y sube, y no baja con
filas. Va en su propio módulo (su propia base): las tablas de la `0037` no admiten filas al bajar y
`aceptacion_de_diferencias`, de sólo agregar, no se vacía desde la app.

L-082: prueba **su** migración (`downgrade 0036` / `upgrade 0037`), nunca "la última".
"""

from __future__ import annotations

import pytest

from ._edificios import BaseDeEdificio
from .test_migracion_0037_borrador_de_saldos import (
    ACCION,
    ACEPTACION,
    CONTROL,
    FILA,
    TABLAS,
    _aceptacion,
    _control,
    _datos,
    _fila,
    _insertar,
    _tablas_existen,
)

pytestmark = pytest.mark.integracion


def _version(base: BaseDeEdificio) -> tuple[object, ...]:
    with base.conectar_migrador() as c:
        return tuple(c.execute("SELECT version_num FROM alembic_version").fetchone() or ())


def _vocabulario(base: BaseDeEdificio) -> list[tuple[object, ...]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre = %s", (ACCION,)
        ).fetchall()


def test_baja_y_sube_conservando_el_vocabulario_y_dejando_la_0036_intacta(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    assert _vocabulario(base) == [(ACCION,)], "la 0037 no cargó la acción en el vocabulario"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0036")
    assert _version(base) == ("0036",)
    assert _vocabulario(base) == []
    with base.conectar_migrador() as c:
        for tabla in TABLAS:
            assert c.execute("SELECT to_regclass(%s)", (f"public.{tabla}",)).fetchone() == (None,)
        assert c.execute(
            "SELECT to_regprocedure('fn_aceptacion_de_diferencias_bloqueada()')"
        ).fetchone() == (None,), "la función del trigger quedó"
        assert c.execute("SELECT to_regclass('public.importacion')").fetchone() != (None,)
    base.roles("antes")
    base.migrar("upgrade", "0037")
    base.roles("despues")
    assert _version(base) == ("0037",)
    assert _vocabulario(base) == [(ACCION,)]


def test_no_baja_con_filas(base_del_edificio: BaseDeEdificio) -> None:
    """Las tres tablas bajan juntas y vacías; cada una sola alcanza para frenar la bajada. La
    aceptación va última: de sólo agregar, no se puede borrar después."""
    base = base_del_edificio
    _tablas_existen(base)
    datos = _datos(base)
    for tabla, escribir in ((CONTROL, _control), (FILA, _fila), (ACEPTACION, _aceptacion)):
        with datos.mundo.conectar() as c:
            _insertar(c, tabla, escribir(datos))
        base.devolver_tablas_protegidas()
        with pytest.raises(AssertionError, match="tiene filas"):
            base.migrar("downgrade", "0036")
        assert _version(base) == ("0037",), f"{tabla}: la bajada rechazada movió la versión"
        base.roles("despues")
        with datos.mundo.conectar() as c:
            assert c.execute(f"SELECT count(*) FROM {tabla}").fetchone() == (1,), (  # noqa: S608
                f"{tabla}: el downgrade rechazado se llevó la fila"
            )
            assert c.execute(
                "SELECT relforcerowsecurity FROM pg_class WHERE relname = %s", (tabla,)
            ).fetchone() == (True,), f"{tabla}: el downgrade rechazado dejó la RLS sin forzar"
        if tabla != ACEPTACION:
            with datos.mundo.conectar() as c:
                c.execute(f"DELETE FROM {tabla}")  # noqa: S608
