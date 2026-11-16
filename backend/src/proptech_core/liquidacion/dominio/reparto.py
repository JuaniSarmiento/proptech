"""Reparto de un monto entre las unidades de un grupo (R01, R07, D-100)."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.reparto import ParteARepartir, clave_de_orden_natural, repartir

Metodo = Literal["coeficiente", "superficie", "partes_iguales"]


class SinBaseDeReparto(ValueError):
    """El grupo tiene gastos pero ninguna unidad con peso para repartirlos."""

    def __init__(self, grupo_id: UUID) -> None:
        self.grupo_id = grupo_id
        super().__init__("el grupo no tiene una base de reparto")


@dataclass(frozen=True)
class UnidadDelPadron:
    id: UUID
    identificador: str
    coeficiente: Decimal
    superficie_m2: Decimal


@dataclass(frozen=True)
class MiembroDelGrupo:
    unidad_id: UUID
    #: Sólo en un grupo de coeficientes propios (D-100); `None` si se renormaliza el de la unidad.
    coeficiente_propio: Decimal | None = None


@dataclass(frozen=True)
class GrupoDelEdificio:
    id: UUID
    nombre: str
    metodo: Metodo
    es_generales: bool
    miembros: tuple[MiembroDelGrupo, ...] = ()


def pesos_del_grupo(
    grupo: GrupoDelEdificio, unidades: Mapping[UUID, UnidadDelPadron]
) -> dict[UUID, Decimal]:
    """El peso de cada unidad en el grupo según su método. Generales no guarda miembros (`0012`):
    incluye a todas las unidades del edificio."""
    if grupo.es_generales:
        miembros = tuple(MiembroDelGrupo(u) for u in unidades)
    else:
        miembros = grupo.miembros
    pesos: dict[UUID, Decimal] = {}
    for miembro in miembros:
        unidad = unidades[miembro.unidad_id]
        if grupo.metodo == "superficie":
            peso = unidad.superficie_m2
        elif grupo.metodo == "partes_iguales":
            peso = Decimal(1)
        elif miembro.coeficiente_propio is not None:
            peso = miembro.coeficiente_propio
        else:
            peso = unidad.coeficiente
        pesos[miembro.unidad_id] = peso
    return pesos


def repartir_en_grupo(
    total: Dinero, grupo: GrupoDelEdificio, unidades: Mapping[UUID, UnidadDelPadron]
) -> dict[UUID, Dinero]:
    """Reparte `total` entre los miembros con `repartir` (mayor resto, orden natural): nunca se
    redondea cada parte por separado (R07, D-046)."""
    pesos = pesos_del_grupo(grupo, unidades)
    if not pesos or not any(p > 0 for p in pesos.values()):
        raise SinBaseDeReparto(grupo.id)
    partes = [
        ParteARepartir(
            unidad_id, peso, clave_de_orden_natural(unidades[unidad_id].identificador, unidad_id)
        )
        for unidad_id, peso in pesos.items()
    ]
    return {UUID(str(k)): v for k, v in repartir(total, partes).items()}
