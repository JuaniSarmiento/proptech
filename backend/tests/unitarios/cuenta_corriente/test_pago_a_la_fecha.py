"""R04 a la fecha de la transferencia (D-166, change 8, H-020), sin base: dos fases."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Deuda, Imputacion
from proptech_core.cuenta_corriente.dominio.pago import imputar_pago_a_la_fecha

INT, ORD = Componente.INTERES, Componente.ORDINARIA
SEPTIEMBRE, OCTUBRE = date(2026, 9, 1), date(2026, 10, 1)


def deuda(obligacion: UUID, componente: Componente, periodo: date, residual: str) -> Deuda:
    return Deuda(obligacion, componente, periodo, periodo.replace(day=10), Dinero(residual))


def test_sin_deuda_posterior_es_el_r04_de_siempre() -> None:
    sep = uuid4()
    deudas = [deuda(sep, INT, SEPTIEMBRE, "2000.00"), deuda(sep, ORD, SEPTIEMBRE, "100000.00")]
    imputaciones, sobrante = imputar_pago_a_la_fecha(deudas, deudas, Dinero("50000.00"))
    assert imputaciones == [
        Imputacion(sep, INT, Dinero("2000.00")),
        Imputacion(sep, ORD, Dinero("48000.00")),
    ]
    assert sobrante == Dinero("0.00")


def test_fase_1_paga_lo_que_existia_ese_dia_antes_que_el_interes_posterior() -> None:
    sep = uuid4()
    al_dia = [deuda(sep, ORD, SEPTIEMBRE, "100000.00")]
    reales = [deuda(sep, INT, SEPTIEMBRE, "2000.00"), *al_dia]
    imputaciones, sobrante = imputar_pago_a_la_fecha(al_dia, reales, Dinero("100000.00"))
    assert imputaciones == [Imputacion(sep, ORD, Dinero("100000.00"))]
    assert sobrante == Dinero("0.00")


def test_fase_2_aplica_el_resto_a_la_deuda_real_que_queda() -> None:
    sep, octubre = uuid4(), uuid4()
    al_dia = [deuda(sep, ORD, SEPTIEMBRE, "100000.00")]
    reales = [
        deuda(sep, INT, SEPTIEMBRE, "2000.00"),
        deuda(sep, ORD, SEPTIEMBRE, "100000.00"),
        deuda(octubre, ORD, OCTUBRE, "1000.00"),
    ]
    imputaciones, sobrante = imputar_pago_a_la_fecha(al_dia, reales, Dinero("101500.00"))
    assert imputaciones == [
        Imputacion(sep, ORD, Dinero("100000.00")),
        Imputacion(sep, INT, Dinero("1500.00")),
    ]
    assert sobrante == Dinero("0.00")


def test_un_mismo_destino_en_las_dos_fases_se_junta() -> None:
    sep = uuid4()
    al_dia = [deuda(sep, INT, SEPTIEMBRE, "300.00")]
    reales = [deuda(sep, INT, SEPTIEMBRE, "2000.00")]
    imputaciones, sobrante = imputar_pago_a_la_fecha(al_dia, reales, Dinero("1000.00"))
    assert imputaciones == [Imputacion(sep, INT, Dinero("1000.00"))]
    assert sobrante == Dinero("0.00")


def test_lo_que_sobra_de_las_dos_fases_es_credito_a_favor() -> None:
    sep = uuid4()
    al_dia = [deuda(sep, ORD, SEPTIEMBRE, "100.00")]
    reales = [deuda(sep, INT, SEPTIEMBRE, "20.00"), *al_dia]
    imputaciones, sobrante = imputar_pago_a_la_fecha(al_dia, reales, Dinero("150.00"))
    assert imputaciones == [
        Imputacion(sep, ORD, Dinero("100.00")),
        Imputacion(sep, INT, Dinero("20.00")),
    ]
    assert sobrante == Dinero("30.00")


def test_sin_deuda_alguna_todo_es_credito_a_favor() -> None:
    assert imputar_pago_a_la_fecha([], [], Dinero("10.00")) == ([], Dinero("10.00"))


def test_el_importe_tiene_que_ser_positivo() -> None:
    with pytest.raises(EntradaInvalida):
        imputar_pago_a_la_fecha([], [], Dinero("0.00"))
