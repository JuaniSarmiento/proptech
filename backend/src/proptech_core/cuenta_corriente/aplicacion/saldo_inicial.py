"""Registro del saldo inicial (R09, design D5 del 4c). Lo llama el 5, que autoriza y audita."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.saldo_inicial import (
    FilaDeCredito,
    FilaDeDeuda,
    FilaDeTotal,
    OrigenDeCarga,
    TotalesDeSaldoInicial,
    UnidadDeSaldoInicial,
)

__all__ = [
    "FilaDeCredito",
    "FilaDeDeuda",
    "FilaDeTotal",
    "OrigenDeCarga",
    "SaldoInicialRegistrado",
    "TotalesDeSaldoInicial",
    "UnidadDeSaldoInicial",
    "registrar_saldo_inicial",
]


@dataclass(frozen=True)
class SaldoInicialRegistrado:
    operacion_id: UUID
    carga_id: UUID
    cuentas: dict[UUID, UUID]
    por_unidad: dict[UUID, TotalesDeSaldoInicial]
    total: TotalesDeSaldoInicial


def registrar_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    operacion_id: UUID,
    fecha_de_migracion: date,
    origen: OrigenDeCarga,
    unidades: Sequence[UnidadDeSaldoInicial],
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> SaldoInicialRegistrado:
    cero = Dinero("0.00")
    vacio = TotalesDeSaldoInicial(cero, cero, cero)
    return SaldoInicialRegistrado(operacion_id, operacion_id, {}, {}, vacio)
