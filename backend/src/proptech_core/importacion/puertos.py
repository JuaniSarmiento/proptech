"""D6 del 6, repetido acá: el caso de uso de importación no sabe que existe Excel. El adaptador real
vive en `adaptadores/excel.py`."""

from __future__ import annotations

from typing import Protocol

from proptech_core.importacion.dominio.plantilla import PlantillaLeida


class LectorDePlantilla(Protocol):
    def leer(self, contenido: bytes, *, nombre: str | None = None) -> PlantillaLeida:
        """Lee la plantilla o levanta `ArchivoInvalido` (con todos los errores de archivo)."""
        ...
