"""H-005 · C04 a C07 y C12: el interés de R03 sobre una obligación migrada corre desde el día
siguiente a la migración, nunca sobre el interés importado (spec `saldo-inicial`, E13, E18).

La emisión de noviembre corta el 31/10; la de diciembre, el 30/11 (E2)."""

from __future__ import annotations

from uuid import UUID

import pytest

from proptech_core.cuenta_corriente.aplicacion import lecturas

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h005 import (
    AGO,
    DIC,
    MES_ENTERO,
    MIGRACION,
    NOV,
    OCT,
    SEP,
    calculado,
    cargar,
    configurar,
    cuenta_de,
    d,
    deuda,
    dia,
    emitir,
    fechas,
    importado,
    obligacion_del,
    pagar,
    sin_calculado,
    total,
    tramos,
    unidad,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def u(mundo: Mundo, n: int) -> UUID:
    return mundo.unidades[n]


def u1_migrada(mundo: Mundo, *, interes_agosto: str = "0.00") -> object:
    return unidad(
        u(mundo, 1),
        deuda(7, AGO, dia(8, 10), "80000.00", interes=interes_agosto),
        deuda(8, SEP, dia(9, 10), "85000.00"),
    )


# --- C04 · El interés importado no entra en la base -----------------------------------------


def test_c04_interes_importado_sin_recalcular(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Interés importado sin recalcular"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u1_migrada(mundo, interes_agosto="4000.00")])
        cuenta = cuenta_de(s, u(mundo, 1))
        agosto = obligacion_del(s, cuenta, AGO)
        i = importado(s, agosto.id)
        assert (i.importe, i.corte) == (d("4000.00"), MIGRACION)
        emitir(s, mundo, NOV)
        # 16 días (16/10 a 31/10) al 3% / 30 sobre $80.000, no sobre $84.000 ($1.344,00).
        assert calculado(s, agosto.id, dia(10, 31)).importe == d("1280.00")


def test_c04_total_unico_con_interes_traido(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Total único con interés traído"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s, mundo, [unidad(u(mundo, 2), total(20, "50000.00", interes="2000.00"), modo="total")]
        )
        cuenta = cuenta_de(s, u(mundo, 2))
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("52000.00")
        o = obligacion_del(s, cuenta, OCT)
        emitir(s, mundo, NOV)
        # 16 días sobre $50.000: $800,00 (sobre $52.000 serían $832,00).
        assert calculado(s, o.id, dia(10, 31)).importe == d("800.00")


# --- C05 · Proporcional después de migrar -----------------------------------------------------


def test_c05_primer_interes_despues_de_migrar(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Primer interés después de migrar"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u1_migrada(mundo)])
        cuenta = cuenta_de(s, u(mundo, 1))
        agosto, septiembre = (obligacion_del(s, cuenta, p) for p in (AGO, SEP))
        emitir(s, mundo, NOV)
        ia = calculado(s, agosto.id, dia(10, 31))
        ise = calculado(s, septiembre.id, dia(10, 31))
        assert (ia.importe, ise.importe) == (d("1280.00"), d("1360.00"))
        for i in (ia, ise):
            ts = tramos(s, i.id)
            assert fechas(ts) == [(dia(10, 16), dia(10, 31))], (
                "corre desde el día siguiente a migrar"
            )
            assert all(t.desde > MIGRACION for t in ts), (
                "un tramo cubre días anteriores a la migración"
            )


# --- C06 · Mes entero después de migrar -------------------------------------------------------


def _mes_entero(base: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base, mundo, forma=MES_ENTERO)


def test_c06_mes_entero_despues_de_migrar(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Mes entero después de migrar"""
    _mes_entero(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u1_migrada(mundo)])
        cuenta = cuenta_de(s, u(mundo, 1))
        agosto, septiembre = (obligacion_del(s, cuenta, p) for p in (AGO, SEP))
        emitir(s, mundo, NOV)
        ia = calculado(s, agosto.id, dia(10, 31))
        ise = calculado(s, septiembre.id, dia(10, 31))
        assert (ia.importe, ise.importe) == (d("2400.00"), d("2550.00"))
        for i in (ia, ise):
            assert fechas(tramos(s, i.id)) == [(dia(10, 16), dia(10, 31))]


def test_c06_mes_entero_despues_de_migrar_con_interes_importado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Mes entero después de migrar, con interés importado"""
    _mes_entero(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u1_migrada(mundo, interes_agosto="4000.00")])
        agosto = obligacion_del(s, cuenta_de(s, u(mundo, 1)), AGO)
        emitir(s, mundo, NOV)
        i = calculado(s, agosto.id, dia(10, 31))
        assert i.importe == d("2400.00")
        assert fechas(tramos(s, i.id)) == [(dia(10, 16), dia(10, 31))]


def test_c06_segundo_mes_despues_de_migrar(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Segundo mes después de migrar"""
    _mes_entero(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [u1_migrada(mundo)])
        agosto = obligacion_del(s, cuenta_de(s, u(mundo, 1)), AGO)
        emitir(s, mundo, NOV)
        emitir(s, mundo, DIC)
        i = calculado(s, agosto.id, dia(11, 30))
        assert i.importe == d("2400.00")
        assert fechas(tramos(s, i.id)) == [(dia(11, 1), dia(11, 30))]


# --- C07 · Total único con gracia -------------------------------------------------------------


def _dos_totales(s: object, mundo: Mundo) -> tuple[UUID, UUID, UUID]:
    cargar(
        s,  # type: ignore[arg-type]
        mundo,
        [
            unidad(u(mundo, 2), total(20, "50000.00"), modo="total"),
            unidad(u(mundo, 3), total(30, "50000.00"), modo="total"),
        ],
    )
    c2 = cuenta_de(s, u(mundo, 2))  # type: ignore[arg-type]
    c3 = cuenta_de(s, u(mundo, 3))  # type: ignore[arg-type]
    return c2, obligacion_del(s, c2, OCT).id, obligacion_del(s, c3, OCT).id  # type: ignore[arg-type]


def test_c07_total_unico_pagado_dentro_de_la_gracia(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Gracia de 5 días desde el vencimiento del total único (la migración, 15/10): pagado el 19/10
    no genera interés. Control: la otra unidad, impaga, sí."""
    configurar(base_del_edificio, mundo, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        c2, o2, o3 = _dos_totales(s, mundo)
        pagar(s, mundo, c2, "50000.00", dia(10, 19))
        emitir(s, mundo, NOV)
        sin_calculado(s, o2)
        assert calculado(s, o3, dia(10, 31)).importe == d("800.00"), "control: la impaga sí"


def test_c07_total_unico_impago_con_gracia(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Impago después de la gracia: corre desde el día siguiente al vencimiento (16/10), no desde el
    fin de la gracia. 16 días sobre $50.000 al 3%: $800,00."""
    configurar(base_del_edificio, mundo, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o2, _ = _dos_totales(s, mundo)
        emitir(s, mundo, NOV)
        i = calculado(s, o2, dia(10, 31))
        assert i.importe == d("800.00")
        assert fechas(tramos(s, i.id)) == [(dia(10, 16), dia(10, 31))]


# --- C12 · Migración el último día del mes ----------------------------------------------------


def test_c12_migracion_el_ultimo_dia_del_mes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Migración el 31/10 con $1.000 de interés importado (corte 31/10): la emisión de noviembre
    (corte 31/10) no tiene días que cobrar ni choca con el importado; la de diciembre cobra del
    01/11 al 30/11, 30 días sobre $100.000: $3.000,00."""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [unidad(u(mundo, 1), deuda(7, SEP, dia(9, 10), "100000.00", interes="1000.00"))],
            fecha=dia(10, 31),
        )
        o = obligacion_del(s, cuenta_de(s, u(mundo, 1)), SEP)
        assert importado(s, o.id).corte == dia(10, 31)
        emitir(s, mundo, NOV)
        sin_calculado(s, o.id)
        emitir(s, mundo, DIC)
        i = calculado(s, o.id, dia(11, 30))
        assert i.importe == d("3000.00")
        assert fechas(tramos(s, i.id)) == [(dia(11, 1), dia(11, 30))]
