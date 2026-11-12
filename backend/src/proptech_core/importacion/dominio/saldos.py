"""PROVISORIO (rojo de la tarea 2.1): `validar_saldos` todavía no valida nada."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from proptech_core.compartido.dinero import Dinero
from proptech_core.importacion.dominio.plantilla import ErrorDeImportacion, PlantillaLeida


@dataclass(frozen=True)
class FilaDeSaldo:
    fila: int
    unidad: str
    tipo: str
    periodo: date | None
    vencimiento: date | None
    concepto: str | None
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class FilaDeControl:
    fila: int
    unidad: str
    saldo: Dinero


@dataclass(frozen=True)
class BorradorValidado:
    filas: tuple[FilaDeSaldo, ...]
    controles: tuple[FilaDeControl, ...]


def validar_saldos(
    plantilla: PlantillaLeida, *, unidades: frozenset[str], fecha_de_migracion: date
) -> tuple[BorradorValidado | None, tuple[ErrorDeImportacion, ...]]:
    return None, ()
