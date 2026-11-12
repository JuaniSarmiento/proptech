"""PROVISORIO (rojo de la tarea 1.5): no agrupa nada."""

from __future__ import annotations

from dataclasses import dataclass

from proptech_core.importacion.dominio.padron import UnidadAImportar
from proptech_core.importacion.dominio.plantilla import ErrorDeImportacion


@dataclass(frozen=True)
class PlanDePropietarios:
    personas: dict[str, str]
    advertencias: tuple[ErrorDeImportacion, ...]


def agrupar_propietarios(unidades: tuple[UnidadAImportar, ...]) -> PlanDePropietarios:
    return PlanDePropietarios(personas={}, advertencias=())
