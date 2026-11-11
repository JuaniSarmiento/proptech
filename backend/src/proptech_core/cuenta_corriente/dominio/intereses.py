"""Cálculo del interés por mora (R03, D2 del 4c), sin base."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import groupby
from typing import Literal
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.compartido.reparto import redondear_al_centavo
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida
from proptech_core.cuenta_corriente.dominio.estado import EstadoDeCuenta, Movimiento, Obligacion
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

FormaDeCalculo = Literal["proporcional_por_dia", "mes_entero"]


@dataclass(frozen=True)
class ConfiguracionDeInteres:
    tasa_mensual: Porcentaje
    dias_de_gracia: int
    forma_de_calculo: FormaDeCalculo


@dataclass(frozen=True)
class TramoDeInteres:
    desde: date
    hasta: date
    dias: int
    base: Dinero


@dataclass(frozen=True)
class InteresCalculado:
    obligacion_id: UUID
    corte: date
    importe: Dinero
    tramos: tuple[TramoDeInteres, ...]


#: R03: el proporcional cobra la tasa mensual repartida en 30 días, sin mirar cuántos tiene el mes.
_DIAS_DEL_MES_COMERCIAL = 30


def _a_decimal(valor: Fraction) -> Decimal:
    # Importes y tasa de dos decimales: el denominador divide a 30.000.000, así que ningún total
    # queda a menos de 3e-8 de un medio centavo y 60 dígitos de división no cambian el redondeo.
    with localcontext() as contexto:
        contexto.prec = 60
        return Decimal(valor.numerator) / Decimal(valor.denominator)


def _dias(desde: date, hasta: date) -> list[date]:
    return [desde + timedelta(days=n) for n in range((hasta - desde).days + 1)]


def _cubiertos(
    obligacion: Obligacion, estado: EstadoDeCuenta, movimientos: Iterable[Movimiento]
) -> set[date]:
    """Unión de los intervalos de los intereses que cuentan de la obligación (E17)."""
    cubiertos: set[date] = set()
    for m in movimientos:
        if (
            m.id in estado.movimientos_que_cuentan
            and m.tipo == "interes"
            and m.obligacion_id == obligacion.id
        ):
            for desde, hasta in m.tramos:
                cubiertos.update(_dias(desde, hasta))
    return cubiertos


def _corte_ocupado(obligacion: Obligacion, corte: date, movimientos: Iterable[Movimiento]) -> bool:
    """Ya hay un interés con ese corte para la obligación, cuente o no (E1, `uq_mov_interes`).

    Un interés anulado o contra-asentado sigue en el libro y ocupa su corte: no se registra otro y
    sus días, que ya no cubren nada, los cobra el primer corte siguiente que registre (E17).
    """
    return any(
        m.tipo == "interes" and m.obligacion_id == obligacion.id and m.corte == corte
        for m in movimientos
    )


def _base_del_dia(
    obligacion: Obligacion,
    estado: EstadoDeCuenta,
    movimientos: dict[UUID, Movimiento],
    dias_de_gracia: int,
) -> Callable[[date], Decimal]:
    """Capital impago de un día: capital y débitos de capital menos imputaciones de capital.

    Nunca suma interés. Un débito o una imputación sube o baja la base desde el día siguiente a su
    fecha. Una imputación con fecha dentro de la gracia se trata como pagada al vencimiento.
    """
    capital = obligacion.ordinaria + obligacion.fondo_de_reserva + obligacion.extraordinaria
    altas = [
        (m.fecha_valor, m.importe.decimal)
        for m in movimientos.values()
        if m.id in estado.movimientos_que_cuentan
        and m.sentido == "debito"
        and m.obligacion_id == obligacion.id
        and m.componente is not None
        and m.componente != Componente.INTERES
    ]
    limite_de_gracia = obligacion.vencimiento + timedelta(days=dias_de_gracia)
    bajas: list[tuple[date, Decimal]] = []
    for parte in estado.imputaciones_que_cuentan:
        if parte.obligacion_id != obligacion.id or parte.componente == Componente.INTERES:
            continue
        credito = movimientos.get(parte.movimiento_id)
        if credito is None:
            raise EntradaInvalida("movimientos", "falta el crédito de una imputación")
        efectiva = (
            obligacion.vencimiento
            if credito.fecha_valor <= limite_de_gracia
            else credito.fecha_valor
        )
        bajas.append((efectiva, parte.importe.decimal))
    base_inicial = capital.decimal

    def base(dia: date) -> Decimal:
        valor = (
            base_inicial
            + sum((i for f, i in altas if f < dia), Decimal(0))
            - sum((i for f, i in bajas if f < dia), Decimal(0))
        )
        return max(valor, Decimal(0))

    return base


def _proporcional(
    dias: list[date], base: Callable[[date], Decimal], tasa: Fraction
) -> tuple[list[TramoDeInteres], Fraction]:
    tramos: list[TramoDeInteres] = []
    total = Fraction(0)
    for dia in dias:
        del_dia = base(dia)
        if del_dia == 0:
            continue
        total += Fraction(del_dia) * tasa / 100 / _DIAS_DEL_MES_COMERCIAL
        if (
            tramos
            and tramos[-1].hasta + timedelta(days=1) == dia
            and tramos[-1].base.decimal == del_dia
        ):
            anterior = tramos[-1]
            tramos[-1] = TramoDeInteres(anterior.desde, dia, anterior.dias + 1, anterior.base)
        else:
            tramos.append(TramoDeInteres(dia, dia, 1, Dinero.desde_decimal(del_dia)))
    return tramos, total


def _mes_entero(
    dias: list[date], base: Callable[[date], Decimal], tasa: Fraction
) -> tuple[list[TramoDeInteres], Fraction]:
    tramos: list[TramoDeInteres] = []
    total = Fraction(0)
    for _, delmes in groupby(dias, key=lambda d: (d.year, d.month)):
        del_mes = list(delmes)
        primero, ultimo = del_mes[0], del_mes[-1]
        if (ultimo - primero).days + 1 != len(del_mes):
            raise EntradaInvalida("dias", "días a cobrar no contiguos dentro de un mes")
        if (ultimo + timedelta(days=1)).day != 1:
            raise EntradaInvalida("corte", "el mes entero necesita un corte en fin de mes")
        del_primero = base(primero)
        if del_primero == 0:
            continue
        total += Fraction(del_primero) * tasa / 100
        tramos.append(
            TramoDeInteres(primero, ultimo, len(del_mes), Dinero.desde_decimal(del_primero))
        )
    return tramos, total


def calcular_intereses(
    estado: EstadoDeCuenta,
    movimientos: Iterable[Movimiento],
    corte: date,
    configuracion: ConfiguracionDeInteres,
) -> tuple[InteresCalculado, ...]:
    """El interés de cada obligación que cuenta hasta `corte`, con su detalle por tramo.

    Cobra los días entre `interes_desde` y el corte que ningún interés que cuenta cubre, con la
    configuración de este corte (E4). Si la obligación ya tiene un interés con este corte, cuente o
    no, no recibe otro (E1). Un importe que redondea a $0,00 no se devuelve y sus días quedan para
    el primer corte que registre (E19). Aritmética exacta; el redondeo ocurre una sola vez, sobre
    la suma de los tramos.
    """
    por_id = {m.id: m for m in movimientos}
    tasa = Fraction(configuracion.tasa_mensual.decimal)
    calculados: list[InteresCalculado] = []
    for obligacion in estado.obligaciones:
        if obligacion.id not in estado.obligaciones_que_cuentan:
            continue
        if (corte - obligacion.vencimiento).days <= configuracion.dias_de_gracia:
            continue
        if _corte_ocupado(obligacion, corte, por_id.values()):
            continue
        cubiertos = _cubiertos(obligacion, estado, por_id.values())
        dias = [d for d in _dias(obligacion.interes_desde, corte) if d not in cubiertos]
        if not dias:
            continue
        base = _base_del_dia(obligacion, estado, por_id, configuracion.dias_de_gracia)
        if configuracion.forma_de_calculo == "mes_entero":
            tramos, total = _mes_entero(dias, base, tasa)
        else:
            tramos, total = _proporcional(dias, base, tasa)
        importe = redondear_al_centavo(_a_decimal(total))
        if importe == Dinero("0.00"):
            continue
        calculados.append(InteresCalculado(obligacion.id, corte, importe, tuple(tramos)))
    return tuple(calculados)
