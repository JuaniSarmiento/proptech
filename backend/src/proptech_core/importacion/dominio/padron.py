"""PROVISORIO (rojo de la tarea 1.3): la validación real del padrón viene en el commit siguiente."""

from __future__ import annotations

from dataclasses import dataclass

from proptech_core.compartido.coeficientes import Coeficiente
from proptech_core.compartido.superficie import Superficie
from proptech_core.importacion.dominio.plantilla import ErrorDeImportacion, PlantillaLeida


@dataclass(frozen=True)
class ContextoDelEdificio:
    """Lo que la validación necesita saber del edificio: nada de la base."""

    #: Los pisos que acepta el edificio (`vocabulario_de_pisos`), o `None` si todavía no configuró
    #: pisos y subsuelos.
    vocabulario_de_pisos: frozenset[str] | None
    tiene_unidades: bool


@dataclass(frozen=True)
class UnidadAImportar:
    fila: int
    identificador: str
    tipo: str
    piso: str
    coeficiente: Coeficiente
    superficie_m2: Superficie
    propietario: str | None
    email: str | None


@dataclass(frozen=True)
class PadronValidado:
    unidades: tuple[UnidadAImportar, ...]
    advertencias: tuple[ErrorDeImportacion, ...]


class PadronInvalido(Exception):
    def __init__(self, errores: list[ErrorDeImportacion]) -> None:
        super().__init__("; ".join(e.motivo for e in errores))
        self.errores = tuple(errores)


def validar_padron(plantilla: PlantillaLeida, contexto: ContextoDelEdificio) -> PadronValidado:
    return PadronValidado(unidades=(), advertencias=())
