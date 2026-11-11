"""Cálculo del interés por mora (R03, D2 del 4c), sin base."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Literal
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.cuenta_corriente.dominio.estado import EstadoDeCuenta, Movimiento

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


def calcular_intereses(
    estado: EstadoDeCuenta,
    movimientos: Iterable[Movimiento],
    corte: date,
    configuracion: ConfiguracionDeInteres,
) -> tuple[InteresCalculado, ...]:
    return ()
