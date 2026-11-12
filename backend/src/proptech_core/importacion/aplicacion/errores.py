"""Errores del caso de uso de importación. La ruta los traduce a HTTP (403 y 409)."""

from __future__ import annotations

from uuid import UUID

from proptech_core.complejos.aplicacion.errores import Conflicto


class SinPermiso(Exception):
    """La persona no tiene el permiso en este edificio (403 con `permiso_faltante`)."""

    def __init__(self, permiso_faltante: str) -> None:
        self.permiso_faltante = permiso_faltante
        super().__init__("sin_permiso")


class ArchivoYaImportado(Conflicto):
    """El mismo archivo (misma huella) ya se importó en el edificio (409, campo `archivo`)."""

    def __init__(self, importacion_id: UUID) -> None:
        self.importacion_id = importacion_id
        super().__init__("archivo")
