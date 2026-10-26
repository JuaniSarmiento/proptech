"""2.2 y 2.3 · Estado de una cuenta y lo que no cuenta (D8, E7, E16, D-085), sin base."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero, MontoInvalido
from proptech_core.cuenta_corriente.dominio.estado import (
    EstadoDeCuenta,
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

INT, ORD, FON, EXT = (
    Componente.INTERES,
    Componente.ORDINARIA,
    Componente.FONDO_DE_RESERVA,
    Componente.EXTRAORDINARIA,
)
CERO = Dinero("0.00")
HOY = datetime(2026, 10, 26, tzinfo=UTC)


def d(texto: str) -> Dinero:
    return Dinero(texto)


def obligacion(
    periodo: date,
    ordinaria: str = "0.00",
    fondo: str = "0.00",
    extraordinaria: str = "0.00",
    emision: UUID | None = None,
) -> Obligacion:
    return Obligacion(
        uuid4(),
        emision,
        periodo,
        periodo.replace(day=10),
        d(ordinaria),
        d(fondo),
        d(extraordinaria),
    )


def credito(importe: str, tipo: str = "pago", **extra: object) -> Movimiento:
    return Movimiento(uuid4(), tipo, "credito", d(importe), date(2026, 10, 1), HOY, **extra)  # type: ignore[arg-type]


def interes(o: Obligacion, importe: str) -> Movimiento:
    return Movimiento(uuid4(), "interes", "debito", d(importe), date(2026, 10, 1), HOY, o.id, INT)


def contra(blanco: Movimiento) -> Movimiento:
    sentido = "credito" if blanco.sentido == "debito" else "debito"
    return Movimiento(
        uuid4(), "correccion", sentido, blanco.importe, date(2026, 10, 2), HOY, corrige_a=blanco.id
    )


class Libro:
    def __init__(self) -> None:
        self.obligaciones: list[Obligacion] = []
        self.movimientos: list[Movimiento] = []
        self.imputaciones: list[ImputacionRegistrada] = []
        self.anuladas: set[UUID] = set()

    def imputa(self, m: Movimiento, o: Obligacion, c: Componente, importe: str) -> None:
        orden = len(self.imputaciones) + 1
        self.imputaciones.append(ImputacionRegistrada(m.id, o.id, c, d(importe), orden))

    def estado(self) -> EstadoDeCuenta:
        return calcular_estado(
            self.obligaciones, self.movimientos, self.imputaciones, self.anuladas
        )


# --- 2.2 ---------------------------------------------------------------------------------------


def test_capital_desglosado_en_tres_componentes() -> None:
    o = obligacion(date(2026, 10, 1), "40000.00", "2000.00", "10000.00")
    e = calcular_estado([o], [], [], [])
    assert e.debido == {
        (o.id, INT): CERO,
        (o.id, ORD): d("40000.00"),
        (o.id, FON): d("2000.00"),
        (o.id, EXT): d("10000.00"),
    }
    assert e.deuda == d("52000.00")


def test_imputaciones_efectivas_reducen_deuda_y_credito_a_favor_por_credito() -> None:
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "50000.00")
    pago = credito("60000.00")
    lb.obligaciones, lb.movimientos = [o], [pago]
    lb.imputa(pago, o, ORD, "50000.00")
    e = lb.estado()
    assert e.residual.get((o.id, ORD)) == CERO
    assert e.deuda == CERO
    assert e.a_favor_por_credito == {pago.id: d("10000.00")}
    assert (e.credito_a_favor, e.credito_a_favor_aplicable) == (d("10000.00"), d("10000.00"))


def test_deuda_total_sin_duplicar_la_obligacion_vieja() -> None:
    """R06: agosto impago aparece una sola vez aunque septiembre también se deba."""
    agosto = obligacion(date(2026, 8, 1), "80000.00")
    septiembre = obligacion(date(2026, 9, 1), "85000.00")
    e = calcular_estado([agosto, septiembre], [], [], [])
    assert e.deuda == d("165000.00")


def test_saldo_anterior_sin_la_emision_pedida() -> None:
    abril_emision = uuid4()
    marzo = obligacion(date(2026, 3, 1), "30000.00", emision=uuid4())
    abril = obligacion(date(2026, 4, 1), "40000.00", emision=abril_emision)
    e = calcular_estado([marzo, abril], [], [], [])
    assert e.deuda_sin_emision(abril_emision) == d("30000.00")


def test_pagar_marzo_lo_saca_del_saldo_anterior() -> None:
    lb = Libro()
    mayo_emision = uuid4()
    marzo = obligacion(date(2026, 3, 1), "30000.00", emision=uuid4())
    mayo = obligacion(date(2026, 5, 1), "40000.00", emision=mayo_emision)
    pago = credito("30000.00")
    lb.obligaciones, lb.movimientos = [marzo, mayo], [pago]
    lb.imputa(pago, marzo, ORD, "30000.00")
    e = lb.estado()
    assert e.deuda_sin_emision(mayo_emision) == CERO
    assert e.deuda == d("40000.00")


def test_saldo_anterior_con_credito_a_favor_es_cero_y_el_favor_va_aparte() -> None:
    lb = Libro()
    emision = uuid4()
    marzo = obligacion(date(2026, 3, 1), "30000.00", emision=uuid4())
    abril = obligacion(date(2026, 4, 1), "40000.00", emision=emision)
    pago = credito("35000.00")
    lb.obligaciones, lb.movimientos = [marzo, abril], [pago]
    lb.imputa(pago, marzo, ORD, "30000.00")
    e = lb.estado()
    assert e.deuda_sin_emision(emision) == CERO
    assert e.credito_a_favor == d("5000.00")


def test_tope_luego_de_corregir_el_interes() -> None:
    """Paso 3: un pago que cubría un interés corregido no deja residual negativo."""
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "40000.00")
    i1 = interes(o, "4000.00")
    pago = credito("4000.00")
    c1 = contra(i1)
    lb.obligaciones, lb.movimientos = [o], [i1, pago, c1]
    lb.imputa(pago, o, INT, "4000.00")
    e = lb.estado()
    assert e.residual.get((o.id, INT)) == CERO
    assert e.imputado.get((o.id, INT)) == CERO
    assert e.a_favor_por_credito[pago.id] == d("4000.00")
    assert e.deuda == d("40000.00")


def test_limite_de_numeric_y_desborde() -> None:
    tope = obligacion(date(2026, 10, 1), "999999999999.99")
    assert calcular_estado([tope], [], [], []).deuda == d("999999999999.99")
    otra = obligacion(date(2026, 11, 1), "0.01")
    with pytest.raises(MontoInvalido):
        calcular_estado([tope, otra], [], [], [])


# --- 2.3 ---------------------------------------------------------------------------------------


def test_anular_deja_la_deuda_como_antes_de_emitir() -> None:
    lb = Libro()
    vieja = obligacion(date(2026, 9, 1), "10000.00", emision=uuid4())
    noviembre_emision = uuid4()
    noviembre = obligacion(date(2026, 11, 1), "40000.00", emision=noviembre_emision)
    pago = credito("40000.00")
    lb.obligaciones, lb.movimientos = [vieja, noviembre], [pago]
    lb.imputa(pago, noviembre, ORD, "40000.00")
    lb.anuladas = {noviembre_emision}
    e = lb.estado()
    assert e.deuda == d("10000.00")
    # El pago imputado a la emisión anulada vuelve como crédito.
    assert e.a_favor_por_credito[pago.id] == d("40000.00")
    assert e.credito_a_favor_aplicable == d("40000.00")


def test_ajuste_que_compensaba_el_interes_anulado_no_cuenta() -> None:
    """D-085: el interés de una emisión anulada se va, y su ajuste enlazado también."""
    lb = Libro()
    emision = uuid4()
    o = obligacion(date(2026, 10, 1), "1000.00", emision=emision)
    i1 = interes(o, "500.00")
    ajuste = credito(
        "500.00", "ajuste_de_interes", obligacion_id=o.id, componente=INT, enlazado_a=i1.id
    )
    lb.obligaciones, lb.movimientos = [o], [i1, ajuste]
    lb.imputa(ajuste, o, INT, "500.00")
    vigente = lb.estado()
    assert ajuste.id in vigente.movimientos_que_cuentan
    assert vigente.deuda == d("1000.00")
    lb.anuladas = {emision}
    e = lb.estado()
    assert ajuste.id not in e.movimientos_que_cuentan
    assert e.credito_a_favor == CERO and e.deuda == CERO


def test_el_par_corregido_no_cuenta_y_no_toca_otros_creditos() -> None:
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "100.00")
    p1, p2 = credito("60.00"), credito("40.00")
    c1 = contra(p1)
    lb.obligaciones, lb.movimientos = [o], [p1, p2, c1]
    lb.imputa(p1, o, ORD, "60.00")
    lb.imputa(p2, o, ORD, "40.00")
    e = lb.estado()
    assert {p1.id, c1.id}.isdisjoint(e.movimientos_que_cuentan)
    assert e.residual.get((o.id, ORD)) == d("60.00")
    assert e.a_favor_por_credito == {p2.id: CERO}


def test_exceso_vuelve_de_la_imputacion_mas_reciente_rc04() -> None:
    """RC-04 en puro: B (fecha valor 15/10) imputó primero, A (fecha valor 1/9) después."""
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "40000.00")
    i1, i2 = interes(o, "4000.00"), interes(o, "6000.00")
    b = Movimiento(uuid4(), "pago", "credito", d("6000.00"), date(2026, 10, 15), HOY)
    a = Movimiento(uuid4(), "pago", "credito", d("4000.00"), date(2026, 9, 1), HOY)
    lb.obligaciones, lb.movimientos = [o], [i1, i2, b, a]
    lb.imputa(b, o, INT, "6000.00")
    lb.imputa(a, o, INT, "4000.00")
    lb.movimientos.append(contra(i1))
    e = lb.estado()
    assert e.a_favor_por_credito == {b.id: CERO, a.id: d("4000.00")}
    assert e.deuda == d("40000.00")


def test_bonificacion_de_emision_anulada_queda_retenida() -> None:
    """E16, RC-13: diciembre debe $40.000; a favor $2.000, aplicable $0, retenido $2.000."""
    lb = Libro()
    nov_emision = uuid4()
    noviembre = obligacion(date(2026, 11, 1), "40000.00", emision=nov_emision)
    diciembre = obligacion(date(2026, 12, 1), "40000.00", emision=uuid4())
    bonif = credito("2000.00", "bonificacion", obligacion_id=noviembre.id, componente=ORD)
    lb.obligaciones, lb.movimientos = [noviembre, diciembre], [bonif]
    lb.imputa(bonif, noviembre, ORD, "2000.00")
    lb.anuladas = {nov_emision}
    e = lb.estado()
    assert e.deuda == d("40000.00")
    assert (e.credito_a_favor, e.credito_a_favor_aplicable, e.credito_a_favor_retenido) == (
        d("2000.00"),
        CERO,
        d("2000.00"),
    )
    assert [x.obligacion_id for x in e.deudas()] == [diciembre.id]


def test_condonacion_cuyo_interes_se_contra_asienta_queda_retenida() -> None:
    """RC2-06: destino que ya no tiene residual: retenido, no aplicable."""
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "40000.00")
    i1 = interes(o, "4000.00")
    cond = credito("4000.00", "condonacion", obligacion_id=o.id, componente=INT)
    lb.obligaciones, lb.movimientos = [o], [i1, cond]
    lb.imputa(cond, o, INT, "4000.00")
    lb.movimientos.append(contra(i1))
    e = lb.estado()
    assert (e.credito_a_favor_aplicable, e.credito_a_favor_retenido) == (CERO, d("4000.00"))


def test_cadena_e6_parte_del_extremo_y_restaura_el_original() -> None:
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "1000.00")
    i1 = interes(o, "300.00")
    c1 = contra(i1)
    c2 = contra(c1)
    lb.obligaciones, lb.movimientos = [o], [i1, c1, c2]
    e = lb.estado()
    assert i1.id in e.movimientos_que_cuentan
    assert {c1.id, c2.id}.isdisjoint(e.movimientos_que_cuentan)
    assert e.residual.get((o.id, INT)) == d("300.00")


def test_pago_con_fecha_valor_anterior_a_una_correccion_no_reescribe_hechos() -> None:
    """AN-12: el cálculo no reordena por fecha valor; las imputaciones son hechos."""
    lb = Libro()
    o = obligacion(date(2026, 10, 1), "100.00")
    nuevo = Movimiento(uuid4(), "pago", "credito", d("100.00"), date(2026, 10, 20), HOY)
    retro = Movimiento(uuid4(), "pago", "credito", d("50.00"), date(2026, 8, 1), HOY)
    lb.obligaciones, lb.movimientos = [o], [nuevo, retro]
    lb.imputa(nuevo, o, ORD, "100.00")
    e = lb.estado()
    assert e.a_favor_por_credito == {nuevo.id: CERO, retro.id: d("50.00")}
