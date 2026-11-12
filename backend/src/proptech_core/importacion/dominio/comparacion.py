"""Comparación pura del borrador de saldos contra el control del administrador (design D6, E13).

El saldo del borrador de una unidad es capital más interés importado menos crédito a favor; la
diferencia es borrador menos control y se mira **por unidad**: un total igual no oculta dos errores
de signo opuesto. Una unidad figura si tiene saldo o control. Sin base ni Excel.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, sumar

_CERO = Dinero("0.00")
_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


@dataclass(frozen=True)
class SaldoGuardado:
    """Una fila de `fila_de_saldo_importada` ya leída (`importe` es >= 0, también el crédito)."""

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
    #: El borrador de la unidad trae capital mayor que cero (ni interés solo ni crédito).
    con_deuda: bool
    aviso: str | None = None


@dataclass(frozen=True)
class Comparacion:
    unidades: tuple[UnidadComparada, ...]
    total_borrador: Dinero
    total_control: Dinero
    unidades_con_diferencia: int


def aviso_de_mes_entero(fecha_de_migracion: date) -> str:
    """E13 (E18 del 4c): con "mes entero" el primer interés del sistema cubre el mes de la
    migración, así que el interés que el Excel ya acumuló puede incluirlo."""
    mes = _MESES[fecha_de_migracion.month - 1]
    return f"El primer interés del sistema cubre {mes} de {fecha_de_migracion.year}"


def comparar_saldos(
    nombres: Mapping[UUID, str], filas: Iterable[SaldoGuardado], controles: Mapping[UUID, Dinero]
) -> Comparacion:
    """`nombres` es el identificador de cada unidad del edificio; las unidades salen ordenadas por
    identificador."""
    capital: dict[UUID, Dinero] = {}
    saldo: dict[UUID, Dinero] = {}
    for fila in filas:
        if fila.tipo == "credito":
            saldo[fila.unidad_id] = saldo.get(fila.unidad_id, _CERO) - fila.importe
            capital.setdefault(fila.unidad_id, _CERO)
        else:
            saldo[fila.unidad_id] = (
                saldo.get(fila.unidad_id, _CERO) + fila.importe + fila.interes_acumulado
            )
            capital[fila.unidad_id] = capital.get(fila.unidad_id, _CERO) + fila.importe
    unidades = []
    for unidad_id in sorted({*saldo, *controles}, key=lambda u: (nombres[u], str(u))):
        borrador = saldo.get(unidad_id, _CERO)
        control = controles.get(unidad_id, _CERO)
        unidades.append(
            UnidadComparada(
                unidad=nombres[unidad_id],
                unidad_id=unidad_id,
                borrador=borrador,
                control=control,
                diferencia=borrador - control,
                con_deuda=capital.get(unidad_id, _CERO) > _CERO,
            )
        )
    return Comparacion(
        unidades=tuple(unidades),
        total_borrador=sumar(u.borrador for u in unidades),
        total_control=sumar(u.control for u in unidades),
        unidades_con_diferencia=sum(1 for u in unidades if u.diferencia != _CERO),
    )
