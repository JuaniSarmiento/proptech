"""7.1 · Clasificación pura de la situación de cobranza (R20, R30, D-109.4, D-143), sin base.

Cada test afirma la situación completa. Los mutantes de la tarea 7.1 están nombrados en `tasks.md`.
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.cobranza import SituacionDeCobranza, clasificar
from proptech_core.cuenta_corriente.dominio.estado import (
    EstadoDeCuenta,
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

AHORA = datetime(2026, 11, 11, tzinfo=UTC)
UMBRAL = Dinero("500.00")
AGO, SEP = date(2026, 8, 10), date(2026, 9, 10)
FIN_DE_OCTUBRE = date(2026, 11, 1)


def d(t: str) -> Dinero:
    return Dinero(t)


def f(mes: int, dia: int) -> date:
    return date(2026, mes, dia)


def obligacion(vence: date, capital: str, *, emision: UUID | None = None) -> Obligacion:
    return Obligacion(
        uuid4(),
        emision,
        vence.replace(day=1),
        vence,
        d(capital),
        d("0.00"),
        d("0.00"),
    )


def interes(obl: Obligacion, importe: str) -> Movimiento:
    return Movimiento(
        uuid4(),
        "interes",
        "debito",
        d(importe),
        obl.vencimiento,
        AHORA,
        obl.id,
        Componente.INTERES,
    )


def pago(importe: str) -> Movimiento:
    return Movimiento(uuid4(), "pago", "credito", d(importe), f(10, 1), AHORA)


def imputa(
    p: Movimiento, o: Obligacion, importe: str, orden: int, comp: Componente = Componente.ORDINARIA
) -> ImputacionRegistrada:
    return ImputacionRegistrada(p.id, o.id, comp, d(importe), orden)


def estado(
    obligaciones: list[Obligacion],
    movimientos: list[Movimiento] | None = None,
    imputaciones: list[ImputacionRegistrada] | None = None,
    anuladas: tuple[UUID, ...] = (),
) -> EstadoDeCuenta:
    return calcular_estado(obligaciones, movimientos or [], imputaciones or [], anuladas)


def situacion(
    e: EstadoDeCuenta, fecha: date = FIN_DE_OCTUBRE, *, gracia: int = 0, umbral: Dinero = UMBRAL
) -> SituacionDeCobranza:
    return clasificar(e, fecha=fecha, dias_de_gracia=gracia, umbral=umbral)


def como_tupla(s: SituacionDeCobranza) -> tuple[str, int, bool, bool, bool, str]:
    return (
        s.total_vencido.a_texto(),
        s.liquidaciones_vencidas,
        s.bajo_umbral,
        s.deuda_de_intereses,
        s.moroso_critico,
        s.etiqueta,
    )


def test_dentro_de_la_gracia_no_esta_vencida_y_al_dia_siguiente_si() -> None:
    e = estado([obligacion(f(9, 10), "85000.00")])
    dentro = situacion(e, f(9, 15), gracia=5)
    assert como_tupla(dentro) == ("0.00", 0, False, False, False, "sin_deuda_vencida")
    fuera = situacion(e, f(9, 16), gracia=5)
    assert como_tupla(fuera) == ("85000.00", 1, False, False, False, "con_deuda_vencida")


def test_el_dia_del_vencimiento_no_esta_vencida() -> None:
    e = estado([obligacion(f(9, 10), "85000.00")])
    assert situacion(e, f(9, 10)).total_vencido == d("0.00")
    assert situacion(e, f(9, 11)).total_vencido == d("85000.00")


def test_emision_anulada_no_cuenta() -> None:
    emision = uuid4()
    e = estado([obligacion(f(9, 10), "85000.00", emision=emision)], anuladas=(emision,))
    assert como_tupla(situacion(e)) == ("0.00", 0, False, False, False, "sin_deuda_vencida")


def test_el_interes_cuenta_en_su_periodo_y_no_como_otra_liquidacion() -> None:
    ago, sep = obligacion(AGO, "80000.00"), obligacion(SEP, "85000.00")
    e = estado([ago, sep], [interes(ago, "4000.00")])
    assert como_tupla(situacion(e)) == ("169000.00", 2, False, False, True, "moroso_critico")


def test_saldo_chico_queda_bajo_el_umbral_y_no_es_moroso() -> None:
    e = estado([obligacion(AGO, "150.00"), obligacion(SEP, "150.00")])
    assert como_tupla(situacion(e)) == ("300.00", 2, True, False, False, "bajo_umbral")


def test_dos_saldos_chicos_que_juntos_pasan_el_umbral() -> None:
    e = estado([obligacion(AGO, "300.00"), obligacion(SEP, "250.00")])
    assert como_tupla(situacion(e)) == ("550.00", 2, False, False, True, "moroso_critico")


def test_justo_en_el_umbral_no_queda_bajo() -> None:
    e = estado([obligacion(AGO, "250.00"), obligacion(SEP, "250.00")])
    assert como_tupla(situacion(e)) == ("500.00", 2, False, False, True, "moroso_critico")


def test_un_centavo_menos_que_el_umbral_queda_bajo() -> None:
    e = estado([obligacion(AGO, "249.99"), obligacion(SEP, "250.00")])
    assert como_tupla(situacion(e)) == ("499.99", 2, True, False, False, "bajo_umbral")


def test_una_sola_vencida_no_es_moroso() -> None:
    e = estado([obligacion(SEP, "85000.00")])
    assert como_tupla(situacion(e)) == ("85000.00", 1, False, False, False, "con_deuda_vencida")


def test_dos_vencidas_con_saldo_es_moroso() -> None:
    e = estado([obligacion(AGO, "80000.00"), obligacion(SEP, "85000.00")])
    assert como_tupla(situacion(e)) == ("165000.00", 2, False, False, True, "moroso_critico")


def test_pago_parcial_que_no_cancela_ninguna_sigue_moroso() -> None:
    ago, sep = obligacion(AGO, "80000.00"), obligacion(SEP, "85000.00")
    p = pago("30000.00")
    e = estado([ago, sep], [p], [imputa(p, ago, "30000.00", 1)])
    assert como_tupla(situacion(e)) == ("135000.00", 2, False, False, True, "moroso_critico")


def test_un_saldo_grande_y_uno_chico_es_moroso() -> None:
    e = estado([obligacion(AGO, "500.00"), obligacion(SEP, "20.00")])
    assert como_tupla(situacion(e)) == ("520.00", 2, False, False, True, "moroso_critico")


def test_un_periodo_con_solo_interes_no_cuenta_como_liquidacion() -> None:
    ago, sep = obligacion(AGO, "80000.00"), obligacion(SEP, "85000.00")
    p = pago("80000.00")
    e = estado([ago, sep], [interes(ago, "4000.00"), p], [imputa(p, ago, "80000.00", 1)])
    assert como_tupla(situacion(e)) == ("89000.00", 1, False, False, False, "con_deuda_vencida")


def test_solo_intereses_es_deuda_de_intereses() -> None:
    ago, sep = obligacion(AGO, "80000.00"), obligacion(SEP, "85000.00")
    p = pago("165000.00")
    e = estado(
        [ago, sep],
        [interes(ago, "4000.00"), p],
        [imputa(p, ago, "80000.00", 1), imputa(p, sep, "85000.00", 2)],
    )
    assert como_tupla(situacion(e)) == ("4000.00", 0, False, True, False, "deuda_de_intereses")


def test_el_interes_chico_queda_bajo_el_umbral_antes_que_deuda_de_intereses() -> None:
    ago = obligacion(AGO, "80000.00")
    p = pago("80000.00")
    e = estado([ago], [interes(ago, "300.00"), p], [imputa(p, ago, "80000.00", 1)])
    assert como_tupla(situacion(e)) == ("300.00", 0, True, False, False, "bajo_umbral")


def test_el_credito_a_favor_no_resta_del_total_vencido() -> None:
    sep = obligacion(SEP, "1000.00")
    e = estado([sep], [pago("3000.00")])
    assert e.credito_a_favor == d("3000.00"), "control: el crédito existe"
    assert como_tupla(situacion(e)) == ("1000.00", 1, False, False, False, "con_deuda_vencida")


def test_lo_no_vencido_no_suma_al_total() -> None:
    e = estado([obligacion(AGO, "80000.00"), obligacion(f(12, 10), "85000.00")])
    assert como_tupla(situacion(e)) == ("80000.00", 1, False, False, False, "con_deuda_vencida")
