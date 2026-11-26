"""H-031 (4d): la `0051_traslado_de_deuda` suma `obligacion.de_traslado` (la única que admite
capital cero), `ck_mov_traslado` y `cambio_de_titular.vendedor_deudor_id`; sube también sobre una
base ya desplegada, con `roles antes` que le presta las tres tablas protegidas (L-089), y no baja
con deuda trasladada. Va en su propio módulo (su propia base). Prueba **su** migración (L-082); los
casos de `CHECK` del libro están en `test_libro_esquema.py`.
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest

from ._edificios import BaseDeEdificio
from ._libro import Libro, sembrar_libro

pytestmark = pytest.mark.integracion


def _version(base: BaseDeEdificio) -> tuple[object, ...]:
    with base.conectar_migrador() as c:
        return tuple(c.execute("SELECT version_num FROM alembic_version").fetchone() or ())


def _columnas(base: BaseDeEdificio, tabla: str) -> set[str]:
    with base.conectar_migrador() as c:
        return {
            str(f[0])
            for f in c.execute(
                "SELECT attname FROM pg_attribute WHERE attrelid = to_regclass(%s) "
                "AND attnum > 0 AND NOT attisdropped",
                (tabla,),
            ).fetchall()
        }


def test_baja_vacia_sube_y_vuelve_a_subir_sobre_una_base_ya_desplegada(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    assert "de_traslado" in _columnas(base, "obligacion")
    assert "vendedor_deudor_id" in _columnas(base, "cambio_de_titular")
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0050")
    assert _version(base) == ("0050",)
    assert "de_traslado" not in _columnas(base, "obligacion"), "bajar la 0051 dejó la columna"
    assert "vendedor_deudor_id" not in _columnas(base, "cambio_de_titular")
    # L-089: una base desplegada (roles devueltos) sube con `roles antes`, que le presta al migrador
    # las tres tablas que la `0051` altera y que `roles despues` devuelve.
    base.roles("despues")
    base.roles("antes")
    base.migrar("upgrade", "0051")
    base.roles("despues")
    assert _version(base) == ("0051",)
    assert "de_traslado" in _columnas(base, "obligacion")


def _contenedora(libro: Libro, **cambios: object) -> None:
    libro.agregar(
        "obligacion",
        cuenta_id=libro.cuenta_personal,
        emision_id=None,
        operacion_id=libro.cuenta_personal,
        ordinaria="0.00",
        fondo_de_reserva="0.00",
        extraordinaria="0.00",
        de_traslado=True,
        **cambios,
    )


def test_una_obligacion_de_traslado_admite_capital_cero_y_una_comun_no(
    base_del_edificio: BaseDeEdificio,
) -> None:
    base = base_del_edificio
    with base.conectar_app() as c:
        c.autocommit = False
        libro = sembrar_libro(c)
        _contenedora(libro, periodo=date(2026, 9, 1))
        with pytest.raises(psycopg.errors.CheckViolation) as e, c.transaction():
            libro.agregar(
                "obligacion",
                cuenta_id=libro.cuenta_personal,
                emision_id=None,
                operacion_id=libro.cuenta,
                ordinaria="0.00",
                fondo_de_reserva="0.00",
                extraordinaria="0.00",
            )
        assert e.value.diag.constraint_name == "ck_obligacion_importes"
        c.rollback()


def test_no_baja_con_una_obligacion_de_traslado(base_del_edificio: BaseDeEdificio) -> None:
    base = base_del_edificio
    with base.conectar_app() as c, c.transaction():
        libro = sembrar_libro(c)
        _contenedora(libro, periodo=date(2026, 9, 1))
    base.devolver_tablas_protegidas()
    with pytest.raises(AssertionError, match="hay deuda trasladada"):
        base.migrar("downgrade", "0050")
    # La bajada es una sola transacción: al rechazarla la 0051 vuelve también la 0052 ya bajada.
    assert _version(base) == ("0052",), "la bajada rechazada movió la versión"
    base.roles("despues")
    with base.conectar_migrador() as c:
        forzadas = c.execute(
            "SELECT relname FROM pg_class WHERE relname IN ('obligacion','movimiento',"
            "'cambio_de_titular') AND NOT relforcerowsecurity"
        ).fetchall()
        assert forzadas == [], "el downgrade rechazado dejó la RLS sin forzar"
