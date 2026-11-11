"""La plantilla de Excel ya leída, sin saber de Excel (design D1 y D3).

Estos tipos los llena el adaptador (`adaptadores/excel.py`) y los consume la validación pura
(`padron.py`). Toda celda llega normalizada a texto o `None`: nunca un `float` (D2).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

#: Límites de D3 (E9): se miden antes de leer filas.
LIMITE_DE_BYTES = 2 * 1024 * 1024
LIMITE_DE_FILAS = 2000

HOJA_UNIDADES = "Unidades"
HOJA_SALDOS = "Saldos"
HOJA_CONTROL = "Control"

#: Hojas y encabezados de la plantilla, en el orden de la plantilla descargada (D1).
ENCABEZADOS_POR_HOJA: Mapping[str, tuple[str, ...]] = {
    HOJA_UNIDADES: (
        "Unidad",
        "Tipo",
        "Piso",
        "Coeficiente",
        "Superficie m2",
        "Propietario",
        "Email",
    ),
    HOJA_SALDOS: (
        "Unidad",
        "Período",
        "Vencimiento",
        "Concepto",
        "Importe",
        "Interés acumulado",
    ),
    HOJA_CONTROL: ("Unidad", "Saldo según el administrador"),
}


@dataclass(frozen=True)
class ErrorDeImportacion:
    """Un error del archivo: `fila` es la del Excel (el encabezado es la fila 1) y es `None` en un
    error de archivo o de hoja; `hoja` y `columna` son `None` donde no aplican."""

    hoja: str | None
    fila: int | None
    columna: str | None
    motivo: str


class ArchivoInvalido(Exception):
    """El archivo no se puede leer (no es un `.xlsx`, supera un límite): no se leen filas."""

    def __init__(self, errores: list[ErrorDeImportacion]) -> None:
        super().__init__("; ".join(e.motivo for e in errores))
        self.errores = tuple(errores)


@dataclass(frozen=True)
class FilaLeida:
    """Una fila de datos. `valores` tiene sólo las columnas de la plantilla (las extras se ignoran),
    cada una como texto exacto de la celda o `None` si está vacía. `formulas_sin_cache` nombra las
    columnas cuya celda es una fórmula sin valor guardado."""

    numero: int
    valores: Mapping[str, str | None]
    formulas_sin_cache: frozenset[str] = frozenset()


@dataclass(frozen=True)
class HojaLeida:
    nombre: str
    #: Los encabezados de la plantilla que la fila 1 trae (nombre exacto), en el orden del archivo.
    encabezados: tuple[str, ...]
    filas: tuple[FilaLeida, ...]


@dataclass(frozen=True)
class PlantillaLeida:
    """Sólo las hojas de la plantilla que el archivo trae, por nombre exacto."""

    hojas: Mapping[str, HojaLeida]
