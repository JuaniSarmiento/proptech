"""Tarea 4.1 de `importacion-desde-excel`: la `0039_ajuste_de_saldo_inicial` crea la tabla de sólo
agregar y la acción, y no baja con filas (el ajuste no se borra). El ciclo completo sube y baja lo
prueba también la aceptación de H-010. Va en su propio módulo (su propia base).

L-082: prueba **su** migración (`downgrade 0038` / `upgrade 0039`), nunca "la última".
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.importacion.aplicacion.confirmar import confirmar

from ._edificios import BaseDeEdificio
from ._importacion import RELOJ, con_tenant, sembrar
from ._saldos_importados import archivo, subir, unidad_de_la_torre
from .test_ajustar_saldo_inicial import MOTIVO, _reloj

pytestmark = pytest.mark.integracion

ACCION = "ajustar_saldo_inicial"
TABLA = "ajuste_de_saldo_inicial"


def _version(base: BaseDeEdificio) -> tuple[object, ...]:
    with base.conectar_migrador() as c:
        return tuple(c.execute("SELECT version_num FROM alembic_version").fetchone() or ())


def _existe(base: BaseDeEdificio) -> bool:
    with base.conectar_migrador() as c:
        fila = c.execute("SELECT to_regclass(%s) IS NOT NULL", (TABLA,)).fetchone()
        return bool(fila and fila[0])


def _vocabulario(base: BaseDeEdificio) -> list[tuple[object, ...]]:
    with base.conectar_migrador() as c:
        return c.execute(
            "SELECT nombre FROM accion_de_auditoria WHERE nombre = %s", (ACCION,)
        ).fetchall()


def test_la_0039_carga_la_tabla_y_la_accion(base_del_edificio: BaseDeEdificio) -> None:
    assert _existe(base_del_edificio), f"la 0039 no creó {TABLA}"
    assert _vocabulario(base_del_edificio) == [(ACCION,)], "la 0039 no cargó la acción"


def test_baja_vacia_y_sube(base_del_edificio: BaseDeEdificio) -> None:
    assert _existe(base_del_edificio), f"la 0039 no creó {TABLA}"
    base = base_del_edificio
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0038")
    assert _version(base) == ("0038",)
    assert not _existe(base), f"bajar la 0039 no sacó {TABLA}"
    assert _vocabulario(base) == [], "bajar la 0039 no sacó la acción"
    with base.conectar_migrador() as c:
        assert c.execute(
            "SELECT to_regprocedure('fn_ajuste_de_saldo_inicial_bloqueada()')"
        ).fetchone() == (None,), "la función del trigger quedó"
    base.roles("antes")
    base.migrar("upgrade", "0039")
    base.roles("despues")
    assert _version(base) == ("0039",)
    assert _existe(base) and _vocabulario(base) == [(ACCION,)]


def test_no_baja_con_ajustes(base_del_edificio: BaseDeEdificio, sesion_edificio: Session) -> None:
    from proptech_core.importacion.aplicacion.ajuste import ajustar_saldo_inicial

    base = base_del_edificio
    mundo = sembrar(base)
    con_tenant(sesion_edificio, mundo.admin)
    importacion = subir(sesion_edificio, mundo.super_admin, mundo.torre, archivo()).importacion_id
    confirmar(
        sesion_edificio,
        mundo.principal,
        complejo_id=mundo.torre,
        importacion_id=importacion,
        reloj=RELOJ,
        request_id=uuid4(),
    )
    ajustar_saldo_inicial(
        sesion_edificio,
        mundo.principal,
        complejo_id=mundo.torre,
        unidad_id=unidad_de_la_torre(sesion_edificio, mundo, "1A"),
        operacion_id=uuid4(),
        importe=Dinero("5000.00"),
        componente="ordinaria",
        motivo=MOTIVO,
        request_id=uuid4(),
        reloj=_reloj(),  # type: ignore[arg-type]
    )
    sesion_edificio.commit()
    base.devolver_tablas_protegidas()
    with pytest.raises(AssertionError, match="tiene filas"):
        base.migrar("downgrade", "0038")
    assert _version(base) == ("0039",), "la bajada rechazada movió la versión"
    base.roles("despues")
    with mundo.conectar() as c:
        assert c.execute(f"SELECT count(*) FROM {TABLA}").fetchone() == (1,)  # noqa: S608
        assert c.execute(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = %s", (TABLA,)
        ).fetchone() == (True,), "el downgrade rechazado dejó la RLS sin forzar"
