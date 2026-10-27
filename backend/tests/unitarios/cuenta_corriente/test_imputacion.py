"""2.1 · Orden de imputación de R04 y destinos fijos (D6, E5, E16), sin base."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida
from proptech_core.cuenta_corriente.dominio.imputacion import (
    ORDEN_DE_IMPUTACION,
    Componente,
    Destino,
    Deuda,
    Imputacion,
    imputar,
)

INT, ORD, FON, EXT = (
    Componente.INTERES,
    Componente.ORDINARIA,
    Componente.FONDO_DE_RESERVA,
    Componente.EXTRAORDINARIA,
)
AGOSTO, SEPTIEMBRE, OCTUBRE = date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)


def d(texto: str) -> Dinero:
    return Dinero(texto)


def deuda(obligacion: UUID, componente: Componente, periodo: date, residual: str) -> Deuda:
    return Deuda(obligacion, componente, periodo, periodo.replace(day=10), d(residual))


def test_orden_de_imputacion_provisorio_de_e5() -> None:
    assert ORDEN_DE_IMPUTACION == (INT, ORD, FON, EXT)


def test_ejemplo_de_r04() -> None:
    agosto, septiembre = UUID(int=2), UUID(int=1)
    # Septiembre se pasa primero y con un id menor: el orden lo decide el período.
    deudas = [
        deuda(septiembre, ORD, SEPTIEMBRE, "85000.00"),
        deuda(agosto, ORD, AGOSTO, "80000.00"),
        deuda(agosto, INT, AGOSTO, "4000.00"),
    ]
    imputaciones, sobrante = imputar(deudas, d("100000.00"))
    assert imputaciones == [
        Imputacion(agosto, INT, d("4000.00")),
        Imputacion(agosto, ORD, d("80000.00")),
        Imputacion(septiembre, ORD, d("16000.00")),
    ]
    assert sobrante == d("0.00")


def test_pago_parcial_cubre_la_ordinaria_antes_que_la_extraordinaria() -> None:
    o = uuid4()
    deudas = [deuda(o, EXT, OCTUBRE, "10000.00"), deuda(o, ORD, OCTUBRE, "40000.00")]
    imputaciones, sobrante = imputar(deudas, d("45000.00"))
    assert imputaciones == [Imputacion(o, ORD, d("40000.00")), Imputacion(o, EXT, d("5000.00"))]
    assert sobrante == d("0.00")


def test_fondo_entre_ordinaria_y_extraordinaria() -> None:
    o = uuid4()
    deudas = [
        deuda(o, EXT, OCTUBRE, "10000.00"),
        deuda(o, FON, OCTUBRE, "2000.00"),
        deuda(o, ORD, OCTUBRE, "40000.00"),
    ]
    imputaciones, _ = imputar(deudas, d("41000.00"))
    assert imputaciones == [Imputacion(o, ORD, d("40000.00")), Imputacion(o, FON, d("1000.00"))]


def test_pago_exacto_de_un_periodo() -> None:
    agosto, septiembre = uuid4(), uuid4()
    deudas = [
        deuda(agosto, ORD, AGOSTO, "80000.00"),
        deuda(agosto, INT, AGOSTO, "4000.00"),
        deuda(septiembre, ORD, SEPTIEMBRE, "85000.00"),
    ]
    imputaciones, sobrante = imputar(deudas, d("84000.00"))
    assert {i.obligacion_id for i in imputaciones} == {agosto}
    assert sumar(i.importe for i in imputaciones) == d("84000.00")
    assert sobrante == d("0.00")


def test_pago_mayor_que_la_deuda_deja_sobrante() -> None:
    o = uuid4()
    imputaciones, sobrante = imputar([deuda(o, ORD, OCTUBRE, "50000.00")], d("60000.00"))
    assert imputaciones == [Imputacion(o, ORD, d("50000.00"))]
    assert sobrante == d("10000.00")


def test_dos_creditos_seguidos_que_superan_la_deuda() -> None:
    o = uuid4()
    primera, sobrante1 = imputar([deuda(o, ORD, OCTUBRE, "10000.00")], d("8000.00"))
    assert primera == [Imputacion(o, ORD, d("8000.00"))] and sobrante1 == d("0.00")
    segunda, sobrante2 = imputar([deuda(o, ORD, OCTUBRE, "2000.00")], d("8000.00"))
    assert segunda == [Imputacion(o, ORD, d("2000.00"))]
    assert sobrante2 == d("6000.00")


def test_condonacion_baja_solo_el_interes_condonado() -> None:
    agosto, julio = uuid4(), uuid4()
    # Julio impago: sin destino fijo, R04 iría primero a julio.
    deudas = [
        deuda(agosto, INT, AGOSTO, "4000.00"),
        deuda(agosto, ORD, AGOSTO, "80000.00"),
        deuda(julio, ORD, date(2026, 7, 1), "1000.00"),
    ]
    imputaciones, sobrante = imputar(deudas, d("4000.00"), Destino(agosto, INT))
    assert imputaciones == [Imputacion(agosto, INT, d("4000.00"))]
    assert sobrante == d("0.00")


def test_ajuste_baja_solo_el_interes_que_compensa() -> None:
    agosto, septiembre = uuid4(), uuid4()
    deudas = [
        deuda(agosto, INT, AGOSTO, "4000.00"),
        deuda(agosto, ORD, AGOSTO, "80000.00"),
        deuda(septiembre, INT, SEPTIEMBRE, "3000.00"),
    ]
    imputaciones, _ = imputar(deudas, d("500.00"), Destino(septiembre, INT))
    assert imputaciones == [Imputacion(septiembre, INT, d("500.00"))]


def test_bonificacion_va_a_la_ordinaria_de_su_periodo() -> None:
    agosto, octubre = uuid4(), uuid4()
    deudas = [deuda(agosto, ORD, AGOSTO, "80000.00"), deuda(octubre, ORD, OCTUBRE, "40000.00")]
    imputaciones, _ = imputar(deudas, d("2000.00"), Destino(octubre, ORD))
    assert imputaciones == [Imputacion(octubre, ORD, d("2000.00"))]


@pytest.mark.parametrize("residual", [None, "1000.00"])
def test_destino_fijo_sin_capacidad_rechaza_todo_el_pedido(residual: str | None) -> None:
    """E16: ni registro parcial ni sobrante libre; diciembre sigue en $40.000."""
    agosto, diciembre = uuid4(), uuid4()
    deudas = [
        deuda(agosto, ORD, AGOSTO, "80000.00"),
        deuda(diciembre, ORD, date(2026, 12, 1), "40000.00"),
    ]
    if residual is not None:
        deudas.append(deuda(agosto, INT, AGOSTO, residual))
    with pytest.raises(EntradaInvalida) as e:
        imputar(deudas, d("4000.00"), Destino(agosto, INT))
    assert e.value.campo == "destino"
    # La emisión siguiente, con R04 y sin el crédito rechazado, queda entera.
    imputaciones, _ = imputar([deudas[1]], d("0.01"))
    assert imputaciones == [Imputacion(diciembre, ORD, d("0.01"))]


@pytest.mark.parametrize("importe", ["0.00", "-1.00"])
@pytest.mark.parametrize("destino", [False, True])
def test_importe_no_positivo(importe: str, destino: bool) -> None:
    o = uuid4()
    with pytest.raises(EntradaInvalida) as e:
        imputar([deuda(o, INT, OCTUBRE, "10.00")], d(importe), Destino(o, INT) if destino else None)
    assert e.value.campo == "importe"


def test_ningun_residual_negativo_ni_float() -> None:
    o = uuid4()
    deudas = [deuda(o, ORD, OCTUBRE, "0.01"), deuda(o, EXT, OCTUBRE, "0.02")]
    imputaciones, sobrante = imputar(deudas, d("1.00"))
    for i in imputaciones:
        residual = next(x.residual for x in deudas if x.componente == i.componente)
        assert i.importe <= residual
        assert isinstance(i.importe, Dinero)
    assert isinstance(sobrante, Dinero) and sobrante == d("0.97")


def test_residual_cero_no_genera_imputacion() -> None:
    o = uuid4()
    imputaciones, sobrante = imputar([deuda(o, ORD, OCTUBRE, "0.00")], d("5.00"))
    assert imputaciones == [] and sobrante == d("5.00")
