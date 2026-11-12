"""PROVISORIO (rojo de la tarea 2.3): la comparación todavía no compara nada."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from proptech_core.compartido.dinero import Dinero


@dataclass(frozen=True)
class SaldoGuardado:
    unidad_id: UUID
    tipo: str
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class UnidadComparada:
    unidad: str
    unidad_id: UUID
    borrador: Dinero
    control: Dinero
    diferencia: Dinero
    con_deuda: bool
    aviso: str | None = None


@dataclass(frozen=True)
class Comparacion:
    unidades: tuple[UnidadComparada, ...]
    total_borrador: Dinero
    total_control: Dinero
    unidades_con_diferencia: int


def comparar_saldos(
    nombres: Mapping[UUID, str], filas: Iterable[SaldoGuardado], controles: Mapping[UUID, Dinero]
) -> Comparacion:
    return Comparacion((), Dinero("0.00"), Dinero("0.00"), 0)


def aviso_de_mes_entero(fecha_de_migracion: date) -> str:
    return ""
