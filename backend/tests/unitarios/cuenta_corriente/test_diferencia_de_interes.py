"""H-021 · la diferencia de interés entre dos bases sobre los mismos tramos (E7, E9), sin base.

El interés se recalcula sobre los tramos guardados con su tasa y su forma, y cada total se redondea
una sola vez (como `calcular_intereses`); la diferencia es el total con la base de antes menos el de
después.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.cuenta_corriente.dominio.intereses import TramoGuardado, diferencia_de_interes

PROP = "proporcional_por_dia"
MES = "mes_entero"


def tramo(desde: date, hasta: date, forma: str = PROP, tasa: str = "3.00") -> TramoGuardado:
    return TramoGuardado(desde, hasta, Porcentaje(tasa), forma)  # type: ignore[arg-type]


def constante(valor: str) -> Callable[[date], Decimal]:
    return lambda _dia: Decimal(valor)


def baja_desde(corte: date, antes: str, despues: str) -> Callable[[date], Decimal]:
    return lambda dia: Decimal(despues) if dia > corte else Decimal(antes)


def test_la_misma_base_da_cero() -> None:
    t = [tramo(date(2026, 11, 1), date(2026, 11, 30))]
    assert diferencia_de_interes(t, constante("100000.00"), constante("100000.00")) == Dinero(
        "0.00"
    )


def test_proporcional_con_la_base_que_baja_a_mitad_del_tramo() -> None:
    # 5 días sobre $100.000 y 25 sobre $2.100, al 3% mensual (0,1% diario): $500 + $52,50 = $552,50.
    t = [tramo(date(2026, 11, 1), date(2026, 11, 30))]
    antes = constante("100000.00")
    despues = baja_desde(date(2026, 11, 5), "100000.00", "2100.00")
    assert diferencia_de_interes(t, antes, despues) == Dinero("2447.50")


def test_proporcional_toda_la_base_en_cero_devuelve_todo_el_interes() -> None:
    t = [tramo(date(2026, 11, 1), date(2026, 11, 30))]
    assert diferencia_de_interes(t, constante("100000.00"), constante("0")) == Dinero("3000.00")


def test_mes_entero_se_cobra_sobre_la_base_del_primer_dia() -> None:
    t = [tramo(date(2026, 11, 1), date(2026, 11, 30), MES)]
    # El pago es del 05/11: el primer día de noviembre la base no cambió, así que no hay diferencia.
    assert diferencia_de_interes(
        t, constante("100000.00"), baja_desde(date(2026, 11, 5), "100000.00", "0")
    ) == Dinero("0.00")
    # Con el pago del 31/10, el 01/11 la base ya es cero: se devuelve el mes entero.
    assert diferencia_de_interes(
        t, constante("100000.00"), baja_desde(date(2026, 10, 31), "100000.00", "0")
    ) == Dinero("3000.00")


def test_redondea_una_sola_vez_sobre_la_suma_de_los_tramos() -> None:
    # Cada tramo de 3 días sobre $1,50 rinde $0,0045 (redondea a $0,00 solo); los dos juntos,
    # $0,009, que redondea a $0,01: el redondeo es uno por total, no uno por tramo.
    t = [
        tramo(date(2026, 11, 1), date(2026, 11, 3)),
        tramo(date(2026, 11, 4), date(2026, 11, 6)),
    ]
    assert diferencia_de_interes(t, constante("1.50"), constante("0")) == Dinero("0.01")


def test_usa_la_tasa_de_cada_tramo() -> None:
    t = [tramo(date(2026, 11, 1), date(2026, 11, 30), tasa="5.00")]
    assert diferencia_de_interes(t, constante("100000.00"), constante("0")) == Dinero("5000.00")


def test_puede_ser_negativa_si_la_base_sube() -> None:
    t = [tramo(date(2026, 11, 1), date(2026, 11, 30))]
    assert diferencia_de_interes(t, constante("0"), constante("100000.00")) == Dinero("-3000.00")
