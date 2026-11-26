"""La deuda de una cuenta a una fecha de corte (H-041, R21, D-171). Sin base."""

from datetime import date, datetime
from uuid import UUID, uuid4

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.a_la_fecha import deuda_a_la_fecha
from proptech_core.cuenta_corriente.dominio.estado import (
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

SEP = Obligacion(
    uuid4(),
    None,
    date(2026, 9, 1),
    date(2026, 9, 10),
    Dinero("1000.00"),
    Dinero("0.00"),
    Dinero("0.00"),
)
OCT = Obligacion(
    uuid4(),
    None,
    date(2026, 10, 1),
    date(2026, 10, 10),
    Dinero("1000.00"),
    Dinero("0.00"),
    Dinero("0.00"),
)
REGISTRADO = datetime(2026, 11, 18, 12)


def _interes(obligacion: Obligacion, importe: str, dia: date) -> Movimiento:
    return Movimiento(
        uuid4(),
        "interes",
        "debito",
        Dinero(importe),
        dia,
        REGISTRADO,
        obligacion.id,
        Componente.INTERES,
    )


def _pago(importe: str, dia: date) -> Movimiento:
    return Movimiento(uuid4(), "pago", "credito", Dinero(importe), dia, REGISTRADO)


def _imputa(
    pago: Movimiento, obligacion: Obligacion, importe: str, orden: int
) -> ImputacionRegistrada:
    return ImputacionRegistrada(
        pago.id, obligacion.id, Componente.ORDINARIA, Dinero(importe), orden
    )


def _a(
    corte: date,
    movimientos: list[Movimiento],
    imputaciones: list[ImputacionRegistrada],
    anuladas: tuple[UUID, ...] = (),
) -> tuple[str, str, list[tuple[date, str]]]:
    deuda = deuda_a_la_fecha([SEP, OCT], movimientos, imputaciones, anuladas, corte)
    return (
        deuda.capital.a_texto(),
        deuda.intereses.a_texto(),
        [(c.vencimiento, c.importe.a_texto()) for c in deuda.cuotas_posteriores],
    )


def test_sin_movimientos_el_capital_son_las_obligaciones_vencidas_y_el_resto_va_aparte() -> None:
    assert _a(date(2026, 9, 30), [], []) == ("1000.00", "0.00", [(date(2026, 10, 10), "1000.00")])
    assert _a(date(2026, 10, 31), [], []) == ("2000.00", "0.00", [])
    assert _a(date(2026, 9, 9), [], []) == (
        "0.00",
        "0.00",
        [(date(2026, 9, 10), "1000.00"), (date(2026, 10, 10), "1000.00")],
    )


def test_el_interes_registrado_cuenta_desde_su_fecha_valor() -> None:
    interes = _interes(SEP, "20.00", date(2026, 9, 30))
    assert _a(date(2026, 9, 29), [interes], [])[1] == "0.00"
    assert _a(date(2026, 9, 30), [interes], [])[:2] == ("1000.00", "20.00")


def test_un_pago_posterior_al_corte_no_resta_y_uno_anterior_si() -> None:
    pago = _pago("400.00", date(2026, 10, 20))
    imputacion = [_imputa(pago, SEP, "400.00", 1)]
    assert _a(date(2026, 10, 19), [pago], imputacion)[0] == "2000.00"
    assert _a(date(2026, 10, 20), [pago], imputacion)[0] == "1600.00"


def test_lo_pagado_de_una_cuota_posterior_baja_lo_pendiente_de_esa_cuota() -> None:
    pago = _pago("300.00", date(2026, 9, 5))
    assert _a(date(2026, 9, 30), [pago], [_imputa(pago, OCT, "300.00", 1)]) == (
        "1000.00",
        "0.00",
        [(date(2026, 10, 10), "700.00")],
    )


def test_una_emision_anulada_no_cuenta() -> None:
    emision = uuid4()
    anulada = Obligacion(
        uuid4(),
        emision,
        date(2026, 8, 1),
        date(2026, 8, 10),
        Dinero("500.00"),
        Dinero("0.00"),
        Dinero("0.00"),
    )
    deuda = deuda_a_la_fecha([SEP, anulada], [], [], [emision], date(2026, 9, 30))
    assert deuda.saldo.a_texto() == "1000.00"
