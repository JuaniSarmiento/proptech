"""PROVISORIO (rojo de la tarea 1.2): el lector real viene en el commit siguiente."""

from __future__ import annotations

from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    HojaLeida,
    PlantillaLeida,
)


class LectorDePlantillaExcel:
    def leer(self, contenido: bytes, *, nombre: str | None = None) -> PlantillaLeida:
        return PlantillaLeida(hojas={n: HojaLeida(n, (), ()) for n in ENCABEZADOS_POR_HOJA})
