"""De las filas validadas a las personas únicas del archivo (design D4, E3). Puro: sin base.

El email identifica a la persona: el mismo email en dos filas es una sola persona propietaria de las
dos unidades (contrato de H-007). Si las dos filas lo escriben con otro nombre se conserva el de la
primera y la segunda suma una advertencia: no es un error del archivo.
"""

from __future__ import annotations

from dataclasses import dataclass

from proptech_core.importacion.dominio.padron import UnidadAImportar
from proptech_core.importacion.dominio.plantilla import HOJA_UNIDADES, ErrorDeImportacion


@dataclass(frozen=True)
class PlanDePropietarios:
    #: email → nombre con el que se crea (o se reusa) la persona; sólo los propietarios con email.
    personas: dict[str, str]
    advertencias: tuple[ErrorDeImportacion, ...]


def agrupar_propietarios(unidades: tuple[UnidadAImportar, ...]) -> PlanDePropietarios:
    personas: dict[str, str] = {}
    primera_fila: dict[str, int] = {}
    advertencias: list[ErrorDeImportacion] = []
    for unidad in unidades:
        if unidad.email is None or unidad.propietario is None:
            continue
        if unidad.email not in personas:
            personas[unidad.email] = unidad.propietario
            primera_fila[unidad.email] = unidad.fila
        elif personas[unidad.email] != unidad.propietario:
            advertencias.append(
                ErrorDeImportacion(
                    HOJA_UNIDADES,
                    unidad.fila,
                    "Propietario",
                    "el mismo email ya estaba en la fila "
                    f"{primera_fila[unidad.email]} con otro nombre: es la misma persona y se "
                    "conserva el nombre de esa fila",
                )
            )
    return PlanDePropietarios(personas=personas, advertencias=tuple(advertencias))
