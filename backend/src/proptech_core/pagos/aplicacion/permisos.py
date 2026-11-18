"""Quién informa y quién ve un pago, por edificio (E4, R10, R11).

El personal con `confirmar_pago_informado` informa por cualquier vecino y ve todo el edificio; un
vecino (propietario o inquilino) sólo informa y ve lo de las unidades donde tiene asignación. El
permiso y el alcance los resuelve la API con `puede` y `alcanza` (404 antes que 403); esto sólo
reparte las unidades.
"""

from collections.abc import Sequence
from uuid import UUID

from proptech_core.acceso.dominio.permisos import Accion, Asignacion, Rol, puede


def es_personal_de_pagos(asignaciones: Sequence[Asignacion], complejo_id: UUID) -> bool:
    return puede(asignaciones, Accion.CONFIRMAR_PAGO_INFORMADO, complejo_id)


def puede_informar_o_ver(asignaciones: Sequence[Asignacion], complejo_id: UUID) -> bool:
    return es_personal_de_pagos(asignaciones, complejo_id) or puede(
        asignaciones, Accion.INFORMAR_PAGO, complejo_id
    )


def unidades_propias(asignaciones: Sequence[Asignacion], complejo_id: UUID) -> frozenset[UUID]:
    """Las unidades del edificio donde la persona tiene una asignación de vecino."""
    return frozenset(
        a.unidad_id
        for a in asignaciones
        if a.rol is Rol.VECINO and a.complejo_id == complejo_id and a.unidad_id is not None
    )


def unidades_del_alcance(
    asignaciones: Sequence[Asignacion], complejo_id: UUID
) -> frozenset[UUID] | None:
    """`None`: todas las del edificio (personal de pagos); si no, las unidades del vecino."""
    if es_personal_de_pagos(asignaciones, complejo_id):
        return None
    return unidades_propias(asignaciones, complejo_id)
