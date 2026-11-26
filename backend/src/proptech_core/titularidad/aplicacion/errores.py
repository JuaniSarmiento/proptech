"""Errores del cambio de titular. La ruta traduce `SinPermiso` a 403; `NoEncontrado` y
`EntradaInvalida` son los de `complejos` (404 y 422)."""

from __future__ import annotations


class SinPermiso(Exception):
    """La persona no tiene el permiso en este edificio (403 con `permiso_faltante`)."""

    def __init__(self, permiso_faltante: str) -> None:
        self.permiso_faltante = permiso_faltante
        super().__init__("sin_permiso")
