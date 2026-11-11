"""H-004 · C01 a C06 y C19 a C22: el interés que registra la emisión, al centavo y con sus tramos.

Cada test arma su propia configuración y su deuda; el importe y las fechas de los tramos salen de la
spec `intereses-por-mora` (recomendaciones E1 a E19 firmadas por Juani el 11/11/2026).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h004 import (
    MES_ENTERO,
    NOV,
    OCT,
    PROPORCIONAL,
    SEP,
    configurar,
    d,
    dia,
    emitir,
    fechas,
    interes_unico,
    intereses_informados,
    obl,
    obligacion_de,
    pagar,
    relleno,
    reloj_del,
    sin_interes,
    tramos,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def septiembre(
    s: Session,
    mundo: Mundo,
    vencimiento: date = date(2026, 9, 10),
    unidad: int = 0,
    **importes: str,
) -> tuple[UUID, UUID]:
    """Emite septiembre con una obligación para `unidad`; devuelve (cuenta, obligación)."""
    r = emitir(s, mundo, SEP, [obl(mundo, unidad, vencimiento, **importes)])
    cuenta = r.cuentas[mundo.unidades[unidad]]
    return cuenta, obligacion_de(s, cuenta, r.emision_id)


# --- C01 · Interés al emitir ------------------------------------------------------------------


def test_c01_expensa_de_septiembre_en_la_emision_de_octubre(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Expensa de septiembre impaga en la emisión de octubre
    Escenario: Saldo anterior con interés"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        r = emitir(s, mundo, OCT, [obl(mundo, 0, dia(10, 10))])
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("2000.00")
        assert i.emision_id == r.emision_id
        assert fechas(tramos(s, i.id)) == [(dia(9, 11), dia(9, 30))]
        assert intereses_informados(r)[cuenta] == [(o, dia(9, 30), d("2000.00"))]
        assert r.saldo_anterior[cuenta] == d("102000.00")


def test_c01_unidad_sin_obligacion_en_la_emision_nueva(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Unidad sin obligación en la emisión nueva"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        r = emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("2000.00")
        assert cuenta in r.saldo_anterior, "la cuenta que sólo recibe interés no está alcanzada"
        assert r.saldo_anterior[cuenta] == d("102000.00")


def test_c01_emitir_a_mitad_de_mes_no_adelanta_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Emitir a mitad de mes no adelanta interés"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT), reloj=reloj_del(dia(10, 15)))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("2000.00")
        assert fechas(tramos(s, octubre.id)) == [(dia(9, 11), dia(9, 30))]
        emitir(s, mundo, NOV, relleno(mundo, NOV), reloj=reloj_del(dia(11, 15)))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("3100.00")
        assert fechas(tramos(s, noviembre.id)) == [(dia(10, 1), dia(10, 31))]


# --- C02 · Simple y sólo sobre el capital ----------------------------------------------------


def test_c02_nunca_interes_sobre_interes(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Nunca interés sobre interés
    Escenario: Lo cubierto por un interés anterior no se vuelve a cobrar"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("2000.00")
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("3100.00"), "la base no es $100.000 (¿suma el interés?)"
        ts = tramos(s, noviembre.id)
        assert fechas(ts) == [(dia(10, 1), dia(10, 31))]
        assert [t.base for t in ts] == [d("100000.00")]


def test_c02_pago_parcial_reduce_la_base(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Pago parcial reduce la base
    Escenario: Detalle de un pago parcial"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        pagar(s, mundo, cuenta, "40000.00", dia(9, 20))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("1600.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 11), dia(9, 20)), (dia(9, 21), dia(9, 30))]
        assert [t.base for t in ts] == [d("100000.00"), d("60000.00")]
        assert [t.dias for t in ts] == [10, 10]
        assert {t.tasa_mensual for t in ts} == {"3.00"}


def test_c02_detalle_de_un_pago_total(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Detalle de un pago total"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        pagar(s, mundo, cuenta, "100000.00", dia(9, 20))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("1000.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 11), dia(9, 20))], "ningún tramo con base cero"
        assert [t.base for t in ts] == [d("100000.00")]


def test_c02_febrero_proporcional(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Febrero proporcional"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        feb, mar = date(2028, 2, 1), date(2028, 3, 1)
        r = emitir(s, mundo, feb, [obl(mundo, 0, date(2028, 2, 10))])
        o = obligacion_de(s, r.cuentas[mundo.unidades[0]], r.emision_id)
        emitir(s, mundo, mar, relleno(mundo, mar))
        i = interes_unico(s, o, date(2028, 2, 29))
        assert i.importe == d("1900.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(date(2028, 2, 11), date(2028, 2, 29))]
        assert [t.dias for t in ts] == [19]


# --- C03 · Gracia de 5 días ------------------------------------------------------------------


def test_c03_pago_dentro_de_la_gracia(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Pago dentro de la gracia"""
    configurar(base_del_edificio, mundo, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10)), obl(mundo, 1, dia(9, 10))])
        c0, c1 = (r.cuentas[mundo.unidades[n]] for n in (0, 1))
        o0, o1 = obligacion_de(s, c0, r.emision_id), obligacion_de(s, c1, r.emision_id)
        pagar(s, mundo, c0, "100000.00", dia(9, 15))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        sin_interes(s, o0)
        assert interes_unico(s, o1, dia(9, 30)).importe == d("2000.00"), "control: la impaga sí"


def test_c03_pago_un_dia_despues_de_la_gracia(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Pago un día después de la gracia"""
    configurar(base_del_edificio, mundo, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        pagar(s, mundo, cuenta, "100000.00", dia(9, 16))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("600.00"), "corre desde el día siguiente al vencimiento"
        assert fechas(tramos(s, i.id)) == [(dia(9, 11), dia(9, 16))]


def test_c03_corte_dentro_de_la_gracia(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Corte dentro de la gracia"""
    configurar(base_del_edificio, mundo, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, dia(9, 28))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("3300.00")
        assert fechas(tramos(s, i.id)) == [(dia(9, 29), dia(10, 31))]
        sin_interes(s, o, dia(9, 30))


# --- C04 · Mes entero ------------------------------------------------------------------------


def test_c04_un_dia_de_atraso_y_el_mes_siguiente(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Un día de atraso con mes entero
    Escenario: El mes siguiente con mes entero"""
    configurar(base_del_edificio, mundo, forma=MES_ENTERO)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, dia(9, 29))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("3000.00")
        assert fechas(tramos(s, octubre.id)) == [(dia(9, 30), dia(9, 30))]
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("3000.00")
        assert fechas(tramos(s, noviembre.id)) == [(dia(10, 1), dia(10, 31))]


def test_c04_corte_dentro_de_la_gracia_con_mes_entero(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Corte dentro de la gracia con mes entero"""
    configurar(base_del_edificio, mundo, forma=MES_ENTERO, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, dia(9, 28))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("6000.00")
        assert fechas(tramos(s, i.id)) == [(dia(9, 29), dia(9, 30)), (dia(10, 1), dia(10, 31))]
        sin_interes(s, o, dia(9, 30))


def test_c04_pago_a_mitad_de_mes_con_mes_entero(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Pago a mitad de mes con mes entero"""
    configurar(base_del_edificio, mundo, forma=MES_ENTERO)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        pagar(s, mundo, cuenta, "40000.00", dia(9, 20))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("3000.00")
        assert [t.base for t in tramos(s, octubre.id)] == [d("100000.00")]
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("1800.00")
        assert [t.base for t in tramos(s, noviembre.id)] == [d("60000.00")]


def test_c04_detalle_de_un_pago_total_con_mes_entero(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Detalle de un pago total con mes entero"""
    configurar(base_del_edificio, mundo, forma=MES_ENTERO)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        pagar(s, mundo, cuenta, "100000.00", dia(9, 20))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("3000.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 11), dia(9, 30))], "en mes entero no se corta en la base cero"
        assert [t.base for t in ts] == [d("100000.00")]


def test_c04_de_proporcional_a_mes_entero(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: De proporcional a mes entero"""
    configurar(base_del_edificio, mundo, forma=PROPORCIONAL)
    configurar(base_del_edificio, mundo, desde=dia(10, 1), forma=MES_ENTERO)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("2000.00")
        assert {t.forma_de_calculo for t in tramos(s, octubre.id)} == {PROPORCIONAL}
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("3000.00"), "un solo mes, no $6.000,00"
        ts = tramos(s, noviembre.id)
        assert fechas(ts) == [(dia(10, 1), dia(10, 31))]
        assert {t.forma_de_calculo for t in ts} == {MES_ENTERO}


def test_c04_de_mes_entero_a_proporcional(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: De mes entero a proporcional"""
    configurar(base_del_edificio, mundo, forma=MES_ENTERO)
    configurar(base_del_edificio, mundo, desde=dia(10, 1), forma=PROPORCIONAL)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, dia(9, 29))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("3000.00")
        assert fechas(tramos(s, octubre.id)) == [(dia(9, 30), dia(9, 30))]
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("3100.00")
        assert fechas(tramos(s, noviembre.id)) == [(dia(10, 1), dia(10, 31))], (
            "sin repetir el 30/09"
        )


# --- C05 · Configuración vigente al corte ----------------------------------------------------


def test_c05_cambio_de_tasa_entre_periodos(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Cambio de tasa entre períodos"""
    v1 = configurar(base_del_edificio, mundo, tasa="3.00")
    v2 = configurar(base_del_edificio, mundo, desde=dia(10, 1), tasa="6.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("2000.00")
        assert {(t.tasa_mensual, t.configuracion_id) for t in tramos(s, octubre.id)} == {
            ("3.00", v1)
        }
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("6200.00")
        assert {(t.tasa_mensual, t.configuracion_id) for t in tramos(s, noviembre.id)} == {
            ("6.00", v2)
        }
        assert interes_unico(s, o, dia(9, 30)).importe == d("2000.00"), "el primero no cambia"


# --- C06 · Redondeo único medio hacia arriba -------------------------------------------------


def test_c06_medio_centavo_hacia_arriba(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Medio centavo hacia arriba"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, dia(9, 28), ordinaria="62.50")
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("0.13")


def test_c06_redondeo_unico_sobre_dos_tramos(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Redondeo único sobre dos tramos"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo, dia(9, 28), ordinaria="64.00")
        pagar(s, mundo, cuenta, "1.00", dia(9, 29))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("0.13"), "redondear cada tramo y sumar da $0,12"
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 29), dia(9, 29)), (dia(9, 30), dia(9, 30))]
        assert [t.base for t in ts] == [d("64.00"), d("63.00")]


# --- C19 a C22 · Bordes que las specs no traen -----------------------------------------------


def test_c19_un_dia_de_atraso_proporcional(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, dia(9, 29))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("100.00")
        assert fechas(tramos(s, i.id)) == [(dia(9, 30), dia(9, 30))]


def test_c20_base_con_los_tres_componentes(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo, ordinaria="70000.00", fondo="10000.00", extra="20000.00")
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        i = interes_unico(s, o, dia(9, 30))
        assert i.importe == d("2000.00")
        assert [t.base for t in tramos(s, i.id)] == [d("100000.00")]


def test_c21_tasa_con_decimales(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo, tasa="2.50")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("1666.67")


def test_c22_pago_imputado_a_interes_y_capital(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("2000.00")
        pagar(s, mundo, cuenta, "30000.00", dia(10, 5))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("2372.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(10, 1), dia(10, 5)), (dia(10, 6), dia(10, 31))]
        assert [t.base for t in ts] == [d("100000.00"), d("72000.00")]
