"""D6 del design: el caso de uso de importación no sabe que existe Excel.
Un puerto con filas ya tipadas; el adaptador real vive en `adaptadores/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FilaCargoImportada:
    """Una fila de la planilla, cruda (sin validar contra el padrón ni
    contra el formato de `Dinero`): eso lo hace el caso de uso, una sola
    vez, para juntar TODOS los errores (D6) en vez de abortar en la
    primera."""

    numero_de_fila: int
    unidad_identificador: str | None
    concepto: str | None
    importe: str | None


class LectorDePlanillaDeCargos(Protocol):
    def leer(self, contenido: bytes) -> list[FilaCargoImportada]: ...
