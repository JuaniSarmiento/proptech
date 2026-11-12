"""Tarea 3.1 de `importacion-desde-excel`: la `0038_confirmar_saldos` sólo agrega la acción
`confirmar_saldos_iniciales` al vocabulario de auditoría; bajarla la saca y deja el esquema de la
`0037` igual (no agrega tablas).

L-082: prueba **su** migración (`downgrade 0037` / `upgrade 0038`), nunca "la última".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion

ACCION = "confirmar_saldos_iniciales"
_VERSIONES = Path(__file__).resolve().parents[2] / "migraciones" / "versions"


def _version(base: BaseDeEdificio) -> tuple[object, ...]:
    with base.conectar_migrador() as c:
        return tuple(c.execute("SELECT version_num FROM alembic_version").fetchone() or ())


def _vocabulario(base: BaseDeEdificio) -> list[tuple[object, ...]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre = %s", (ACCION,)
        ).fetchall()


def _tablas(base: BaseDeEdificio) -> list[tuple[object, ...]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
        ).fetchall()


def test_la_0038_carga_la_accion_en_el_vocabulario(base_del_edificio: BaseDeEdificio) -> None:
    assert _vocabulario(base_del_edificio) == [(ACCION,)], "la 0038 no cargó la acción"


def test_baja_y_sube_dejando_la_0037_intacta(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    assert list(_VERSIONES.glob("0038_*.py")), "falta la migración 0038 (confirmar saldos)"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0038")  # la 0039 baja antes: las tablas se comparan sin la suya
    tablas = _tablas(base)
    base.migrar("downgrade", "0037")
    assert _version(base) == ("0037",)
    assert _vocabulario(base) == [], "bajar la 0038 no sacó la acción"
    assert _tablas(base) == tablas, "la 0038 no agrega ni saca tablas"
    base.roles("antes")
    base.migrar("upgrade", "0038")
    base.roles("despues")
    assert _version(base) == ("0038",), "la subida a la 0038 no quedó aplicada"
    assert _vocabulario(base) == [(ACCION,)]
    assert _tablas(base) == tablas
    base.roles("antes")
    base.migrar("upgrade", "head")  # de nuevo en la cabeza para el resto del módulo
    base.roles("despues")
