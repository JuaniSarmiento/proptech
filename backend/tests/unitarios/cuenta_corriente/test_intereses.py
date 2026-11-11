"""4.1 a 4.3 · Cálculo puro del interés por mora (R03, D2 del 4c), sin base.

Cada test afirma el importe y las fechas de los tramos. Los escenarios de saldo inicial ("Primer
interés después de migrar", "Mes entero después de migrar", "Segundo mes después de migrar") van al
final de este archivo: el dominio recibe `interes_desde` (el día siguiente a la migración) y el
interés importado no entra en la base.
"""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida
from proptech_core.cuenta_corriente.dominio.estado import (
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente
from proptech_core.cuenta_corriente.dominio.intereses import (
    ConfiguracionDeInteres,
    FormaDeCalculo,
    InteresCalculado,
    calcular_intereses,
)

HOY = datetime(2026, 11, 11, tzinfo=UTC)
PROP: FormaDeCalculo = "proporcional_por_dia"
MES: FormaDeCalculo = "mes_entero"

Tramo = tuple[date, date, int, str]


def f(mes: int, dia: int, anio: int = 2026) -> date:
    return date(anio, mes, dia)


def cobro(
    vencimiento: date,
    corte: date,
    *,
    capital: str = "100000.00",
    tasa: str = "3.00",
    gracia: int = 0,
    forma: FormaDeCalculo = PROP,
    pagos: tuple[tuple[str, date], ...] = (),
    previos: tuple[tuple[str, date, tuple[tuple[date, date], ...]], ...] = (),
    debitos: tuple[tuple[str, date], ...] = (),
    interes_desde: date | None = None,
) -> tuple[InteresCalculado, ...]:
    """Arma el estado de una cuenta con una obligación y calcula el interés al corte."""
    o = Obligacion(
        uuid4(),
        None,
        vencimiento.replace(day=1),
        vencimiento,
        Dinero(capital),
        Dinero("0.00"),
        Dinero("0.00"),
        interes_desde=interes_desde or date.min,
    )
    movimientos: list[Movimiento] = []
    imputaciones: list[ImputacionRegistrada] = []
    for orden, (importe, fecha) in enumerate(pagos, start=1):
        pago = Movimiento(uuid4(), "pago", "credito", Dinero(importe), fecha, HOY)
        movimientos.append(pago)
        imputaciones.append(
            ImputacionRegistrada(pago.id, o.id, Componente.ORDINARIA, Dinero(importe), orden)
        )
    for importe, fecha in debitos:
        movimientos.append(
            Movimiento(
                uuid4(), "ajuste", "debito", Dinero(importe), fecha, HOY, o.id, Componente.ORDINARIA
            )
        )
    for importe, corte_previo, tramos in previos:
        movimientos.append(
            Movimiento(
                uuid4(),
                "interes",
                "debito",
                Dinero(importe),
                corte_previo,
                HOY,
                o.id,
                Componente.INTERES,
                corte=corte_previo,
                tramos=tramos,
            )
        )
    estado = calcular_estado([o], movimientos, imputaciones, [])
    configuracion = ConfiguracionDeInteres(Porcentaje(tasa), gracia, forma)
    return calcular_intereses(estado, movimientos, corte, configuracion)


def unico(resultado: tuple[InteresCalculado, ...]) -> InteresCalculado:
    assert len(resultado) == 1, f"se esperaba un interés y hay {len(resultado)}"
    return resultado[0]


def detalle(interes: InteresCalculado) -> list[Tramo]:
    return [(t.desde, t.hasta, t.dias, t.base.a_texto()) for t in interes.tramos]


# ---------------------------------------------------------------------------------------------
# 4.1 · Proporcional, base, nunca interés sobre interés, tasa cero y redondeo único
# ---------------------------------------------------------------------------------------------


def test_expensa_de_septiembre_impaga_en_la_emision_de_octubre() -> None:
    interes = unico(cobro(f(9, 10), f(9, 30)))
    assert interes.importe == Dinero("2000.00")
    assert interes.corte == f(9, 30)
    assert detalle(interes) == [(f(9, 11), f(9, 30), 20, "100000.00")]


def test_nunca_interes_sobre_interes() -> None:
    interes = unico(
        cobro(f(9, 10), f(10, 31), previos=(("2000.00", f(9, 30), ((f(9, 11), f(9, 30)),)),))
    )
    assert interes.importe == Dinero("3100.00")
    assert detalle(interes) == [(f(10, 1), f(10, 31), 31, "100000.00")]


def test_pago_parcial_reduce_la_base() -> None:
    interes = unico(cobro(f(9, 10), f(9, 30), pagos=(("40000.00", f(9, 20)),)))
    assert interes.importe == Dinero("1600.00")
    assert detalle(interes) == [
        (f(9, 11), f(9, 20), 10, "100000.00"),
        (f(9, 21), f(9, 30), 10, "60000.00"),
    ]


def test_tasa_cero() -> None:
    assert cobro(f(9, 10), f(9, 30), tasa="0.00") == ()


def test_medio_centavo_hacia_arriba() -> None:
    interes = unico(cobro(f(9, 28), f(9, 30), capital="62.50"))
    assert interes.importe == Dinero("0.13")
    assert detalle(interes) == [(f(9, 29), f(9, 30), 2, "62.50")]


def test_redondeo_unico_sobre_dos_tramos() -> None:
    interes = unico(cobro(f(9, 28), f(9, 30), capital="64.00", pagos=(("1.00", f(9, 29)),)))
    assert interes.importe == Dinero("0.13")
    assert detalle(interes) == [
        (f(9, 29), f(9, 29), 1, "64.00"),
        (f(9, 30), f(9, 30), 1, "63.00"),
    ]


def test_detalle_de_un_pago_total() -> None:
    interes = unico(cobro(f(9, 10), f(9, 30), pagos=(("100000.00", f(9, 20)),)))
    assert interes.importe == Dinero("1000.00")
    assert detalle(interes) == [(f(9, 11), f(9, 20), 10, "100000.00")]


def test_un_debito_de_capital_suma_a_la_base_desde_el_dia_siguiente() -> None:
    interes = unico(cobro(f(9, 10), f(9, 30), debitos=(("50000.00", f(9, 20)),)))
    # 10 días sobre $100.000 (11 a 20) y 10 sobre $150.000 (21 a 30): 1.000 + 1.500.
    assert interes.importe == Dinero("2500.00")
    assert detalle(interes) == [
        (f(9, 11), f(9, 20), 10, "100000.00"),
        (f(9, 21), f(9, 30), 10, "150000.00"),
    ]


# ---------------------------------------------------------------------------------------------
# 4.2 · Gracia e inicio natural
# ---------------------------------------------------------------------------------------------


def test_pago_dentro_de_la_gracia() -> None:
    assert cobro(f(9, 10), f(9, 30), gracia=5, pagos=(("100000.00", f(9, 15)),)) == ()


def test_pago_un_dia_despues_de_la_gracia() -> None:
    interes = unico(cobro(f(9, 10), f(9, 30), gracia=5, pagos=(("100000.00", f(9, 16)),)))
    assert interes.importe == Dinero("600.00")
    assert detalle(interes) == [(f(9, 11), f(9, 16), 6, "100000.00")]


def test_corte_dentro_de_la_gracia() -> None:
    assert cobro(f(9, 28), f(9, 30), gracia=5) == ()
    interes = unico(cobro(f(9, 28), f(10, 31), gracia=5))
    assert interes.importe == Dinero("3300.00")
    assert detalle(interes) == [(f(9, 29), f(10, 31), 33, "100000.00")]


def test_corte_en_el_ultimo_dia_de_la_gracia_no_cobra() -> None:
    # vence 25/09, gracia 5: el 30/09 es el quinto día de atraso, todavía dentro.
    assert cobro(f(9, 25), f(9, 30), gracia=5) == ()
    assert unico(cobro(f(9, 24), f(9, 30), gracia=5)).importe == Dinero("600.00")


def test_lo_cubierto_por_un_interes_anterior_no_se_vuelve_a_cobrar() -> None:
    interes = unico(
        cobro(f(9, 10), f(10, 31), previos=(("2000.00", f(9, 30), ((f(9, 11), f(9, 30)),)),))
    )
    assert interes.tramos[0].desde == f(10, 1)


def test_el_inicio_de_una_obligacion_migrada_es_el_que_pasa_el_lector() -> None:
    # No es el escenario de H-005: sólo que el dominio respeta `interes_desde`.
    interes = unico(cobro(f(8, 10), f(10, 31), capital="80000.00", interes_desde=f(10, 16)))
    assert interes.importe == Dinero("1280.00")
    assert detalle(interes) == [(f(10, 16), f(10, 31), 16, "80000.00")]


# ---------------------------------------------------------------------------------------------
# 4.3 · Mes entero por meses calendario
# ---------------------------------------------------------------------------------------------


def test_un_dia_de_atraso_con_mes_entero() -> None:
    interes = unico(cobro(f(9, 29), f(9, 30), forma=MES))
    assert interes.importe == Dinero("3000.00")
    assert detalle(interes) == [(f(9, 30), f(9, 30), 1, "100000.00")]


def test_el_mes_siguiente_con_mes_entero() -> None:
    interes = unico(
        cobro(
            f(9, 29),
            f(10, 31),
            forma=MES,
            previos=(("3000.00", f(9, 30), ((f(9, 30), f(9, 30)),)),),
        )
    )
    assert interes.importe == Dinero("3000.00")
    assert detalle(interes) == [(f(10, 1), f(10, 31), 31, "100000.00")]


def test_corte_dentro_de_la_gracia_con_mes_entero() -> None:
    assert cobro(f(9, 28), f(9, 30), gracia=5, forma=MES) == ()
    interes = unico(cobro(f(9, 28), f(10, 31), gracia=5, forma=MES))
    assert interes.importe == Dinero("6000.00")
    assert detalle(interes) == [
        (f(9, 29), f(9, 30), 2, "100000.00"),
        (f(10, 1), f(10, 31), 31, "100000.00"),
    ]


def test_pago_a_mitad_de_mes_con_mes_entero() -> None:
    pagos = (("40000.00", f(9, 20)),)
    septiembre = unico(cobro(f(9, 10), f(9, 30), forma=MES, pagos=pagos))
    assert septiembre.importe == Dinero("3000.00")
    assert detalle(septiembre) == [(f(9, 11), f(9, 30), 20, "100000.00")]
    octubre = unico(
        cobro(
            f(9, 10),
            f(10, 31),
            forma=MES,
            pagos=pagos,
            previos=(("3000.00", f(9, 30), ((f(9, 11), f(9, 30)),)),),
        )
    )
    assert octubre.importe == Dinero("1800.00")
    assert detalle(octubre) == [(f(10, 1), f(10, 31), 31, "60000.00")]


def test_febrero_proporcional() -> None:
    interes = unico(cobro(f(2, 10, 2028), f(2, 29, 2028)))
    assert interes.importe == Dinero("1900.00")
    assert detalle(interes) == [(f(2, 11, 2028), f(2, 29, 2028), 19, "100000.00")]


def test_de_proporcional_a_mes_entero() -> None:
    interes = unico(
        cobro(
            f(9, 10),
            f(10, 31),
            forma=MES,
            previos=(("2000.00", f(9, 30), ((f(9, 11), f(9, 30)),)),),
        )
    )
    assert interes.importe == Dinero("3000.00")
    assert detalle(interes) == [(f(10, 1), f(10, 31), 31, "100000.00")]


def test_de_mes_entero_a_proporcional() -> None:
    interes = unico(
        cobro(
            f(9, 29),
            f(10, 31),
            forma=PROP,
            previos=(("3000.00", f(9, 30), ((f(9, 30), f(9, 30)),)),),
        )
    )
    assert interes.importe == Dinero("3100.00")
    assert detalle(interes) == [(f(10, 1), f(10, 31), 31, "100000.00")]


def test_detalle_de_un_pago_total_con_mes_entero() -> None:
    interes = unico(cobro(f(9, 10), f(9, 30), forma=MES, pagos=(("100000.00", f(9, 20)),)))
    assert interes.importe == Dinero("3000.00")
    assert detalle(interes) == [(f(9, 11), f(9, 30), 20, "100000.00")]


def test_mes_entero_respeta_el_inicio_que_pasa_el_lector() -> None:
    # No es el escenario de H-005: el mes de la migración cobra desde el primer día a cobrar.
    interes = unico(
        cobro(f(8, 10), f(10, 31), capital="80000.00", forma=MES, interes_desde=f(10, 16))
    )
    assert interes.importe == Dinero("2400.00")
    assert detalle(interes) == [(f(10, 16), f(10, 31), 16, "80000.00")]


def test_dias_no_contiguos_dentro_de_un_mes_entero_lanzan_y_no_devuelven_importe() -> None:
    previos = (("1.00", f(10, 10), ((f(10, 5), f(10, 10)),)),)
    with pytest.raises(EntradaInvalida):
        cobro(f(9, 30), f(10, 31), forma=MES, previos=previos)


def test_mes_entero_con_un_corte_que_no_es_fin_de_mes_lanza() -> None:
    with pytest.raises(EntradaInvalida):
        cobro(f(9, 10), f(10, 15), forma=MES)


def test_los_dias_no_cobrados_no_pasan_el_corte() -> None:
    # Una obligación que vence después del corte no cobra nada.
    assert cobro(f(10, 10), f(9, 30)) == ()


# ---------------------------------------------------------------------------------------------
# 4.4 · Huecos: días de un interés que no cuenta y de un corte sin importe (E1, E17, E19)
# ---------------------------------------------------------------------------------------------


class Libro:
    """Una obligación y su libro de intereses: encadena cortes como lo hace la emisión.

    `emitir` calcula con el estado actual y registra lo que el dominio devuelve; `anular` deja el
    interés de un corte en el libro, sin contar (contra-asiento), como lo hace la corrección.
    """

    def __init__(self, vencimiento: date, capital: str = "100000.00") -> None:
        self.obligacion = Obligacion(
            uuid4(),
            None,
            vencimiento.replace(day=1),
            vencimiento,
            Dinero(capital),
            Dinero("0.00"),
            Dinero("0.00"),
        )
        self.movimientos: list[Movimiento] = []

    def emitir(
        self, corte: date, tasa: str = "3.00", forma: FormaDeCalculo = PROP, gracia: int = 0
    ) -> tuple[InteresCalculado, ...]:
        estado = calcular_estado([self.obligacion], self.movimientos, [], [])
        configuracion = ConfiguracionDeInteres(Porcentaje(tasa), gracia, forma)
        resultado = calcular_intereses(estado, self.movimientos, corte, configuracion)
        for interes in resultado:
            self.movimientos.append(
                Movimiento(
                    uuid4(),
                    "interes",
                    "debito",
                    interes.importe,
                    interes.corte,
                    HOY,
                    self.obligacion.id,
                    Componente.INTERES,
                    corte=interes.corte,
                    tramos=tuple((t.desde, t.hasta) for t in interes.tramos),
                )
            )
        return resultado

    def anular(self, corte: date) -> None:
        interes = next(
            m
            for m in reversed(self.movimientos)
            if m.tipo == "interes"
            and m.corte == corte
            and not any(c.corrige_a == m.id for c in self.movimientos)
        )
        self.movimientos.append(
            Movimiento(
                uuid4(),
                "contra_asiento",
                "credito",
                interes.importe,
                interes.fecha_valor,
                HOY,
                self.obligacion.id,
                Componente.INTERES,
                corrige_a=interes.id,
            )
        )


def test_anular_y_volver_a_emitir_no_cobra_dos_veces() -> None:
    libro = Libro(f(9, 10))
    assert unico(libro.emitir(f(9, 30))).importe == Dinero("2000.00")
    libro.anular(f(9, 30))
    assert libro.emitir(f(9, 30)) == (), "ninguno nuevo: el corte ya lo ocupa el interés anulado"


def test_un_corte_con_un_interes_que_cuenta_no_recibe_otro() -> None:
    libro = Libro(f(9, 10))
    assert unico(libro.emitir(f(9, 30))).importe == Dinero("2000.00")
    assert libro.emitir(f(9, 30)) == ()


def test_el_corte_siguiente_recupera_el_tramo() -> None:
    libro = Libro(f(9, 10))
    libro.emitir(f(9, 30))
    libro.anular(f(9, 30))
    libro.emitir(f(9, 30))
    interes = unico(libro.emitir(f(10, 31)))
    assert interes.importe == Dinero("5100.00")
    assert detalle(interes) == [(f(9, 11), f(10, 31), 51, "100000.00")]


def test_el_tramo_recuperado_usa_la_tasa_del_corte_siguiente() -> None:
    libro = Libro(f(9, 10))
    libro.emitir(f(9, 30), tasa="3.00")
    libro.anular(f(9, 30))
    assert libro.emitir(f(9, 30), tasa="3.00") == ()
    interes = unico(libro.emitir(f(10, 31), tasa="6.00"))
    assert interes.importe == Dinero("10200.00")
    assert detalle(interes) == [(f(9, 11), f(10, 31), 51, "100000.00")]


def test_un_hueco_anterior_se_recupera_aunque_haya_un_interes_posterior() -> None:
    libro = Libro(f(9, 10))
    assert unico(libro.emitir(f(9, 30))).importe == Dinero("2000.00")
    assert unico(libro.emitir(f(10, 31))).importe == Dinero("3100.00")
    libro.anular(f(9, 30))
    interes = unico(libro.emitir(f(11, 30)))
    assert interes.importe == Dinero("5000.00")
    assert detalle(interes) == [
        (f(9, 11), f(9, 30), 20, "100000.00"),
        (f(11, 1), f(11, 30), 30, "100000.00"),
    ]


def test_los_dias_de_un_corte_con_tasa_cero_se_cobran_despues() -> None:
    libro = Libro(f(9, 10))
    assert libro.emitir(f(9, 30), tasa="0.00") == ()
    interes = unico(libro.emitir(f(10, 31), tasa="3.00"))
    assert interes.importe == Dinero("5100.00")
    assert detalle(interes) == [(f(9, 11), f(10, 31), 51, "100000.00")]


def test_un_corte_sin_importe_por_base_chica_no_pierde_sus_centavos() -> None:
    # $1,00 un día al 3%: $0,001 redondea a $0,00 y no registra; 32 días valen $0,032 = $0,03.
    libro = Libro(f(9, 29), capital="1.00")
    assert libro.emitir(f(9, 30)) == ()
    interes = unico(libro.emitir(f(10, 31)))
    assert interes.importe == Dinero("0.03")
    assert detalle(interes) == [(f(9, 30), f(10, 31), 32, "1.00")]


# ---------------------------------------------------------------------------------------------
# H-005 · 4.2 y 4.3 · escenarios de saldo inicial (migración el 15/10/2026, E13, E18)
# ---------------------------------------------------------------------------------------------

MIGRACION_SIGUIENTE = f(10, 16)


def test_primer_interes_despues_de_migrar() -> None:
    agosto = unico(
        cobro(f(8, 10), f(10, 31), capital="80000.00", interes_desde=MIGRACION_SIGUIENTE)
    )
    septiembre = unico(
        cobro(f(9, 10), f(10, 31), capital="85000.00", interes_desde=MIGRACION_SIGUIENTE)
    )
    assert (agosto.importe, septiembre.importe) == (Dinero("1280.00"), Dinero("1360.00"))
    assert detalle(agosto) == [(f(10, 16), f(10, 31), 16, "80000.00")]
    assert detalle(septiembre) == [(f(10, 16), f(10, 31), 16, "85000.00")]


def test_mes_entero_despues_de_migrar() -> None:
    agosto = unico(
        cobro(
            f(8, 10),
            f(10, 31),
            capital="80000.00",
            forma=MES,
            interes_desde=MIGRACION_SIGUIENTE,
        )
    )
    septiembre = unico(
        cobro(
            f(9, 10),
            f(10, 31),
            capital="85000.00",
            forma=MES,
            interes_desde=MIGRACION_SIGUIENTE,
        )
    )
    assert (agosto.importe, septiembre.importe) == (Dinero("2400.00"), Dinero("2550.00"))
    assert detalle(agosto) == [(f(10, 16), f(10, 31), 16, "80000.00")]
    assert detalle(septiembre) == [(f(10, 16), f(10, 31), 16, "85000.00")]


def test_mes_entero_despues_de_migrar_con_interes_importado_no_suma_a_la_base() -> None:
    # El interés importado ($4.000, corte en la migración, sin tramos) no entra en la base.
    interes = unico(
        cobro(
            f(8, 10),
            f(10, 31),
            capital="80000.00",
            forma=MES,
            previos=(("4000.00", f(10, 15), ()),),
            interes_desde=MIGRACION_SIGUIENTE,
        )
    )
    assert interes.importe == Dinero("2400.00")
    assert detalle(interes) == [(f(10, 16), f(10, 31), 16, "80000.00")]


def test_segundo_mes_despues_de_migrar() -> None:
    interes = unico(
        cobro(
            f(8, 10),
            f(11, 30),
            capital="80000.00",
            forma=MES,
            previos=(("2400.00", f(10, 31), ((f(10, 16), f(10, 31)),)),),
            interes_desde=MIGRACION_SIGUIENTE,
        )
    )
    assert interes.importe == Dinero("2400.00")
    assert detalle(interes) == [(f(11, 1), f(11, 30), 30, "80000.00")]
