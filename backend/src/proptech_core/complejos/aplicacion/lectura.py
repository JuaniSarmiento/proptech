"""Lectura mínima de `complejo`/`unidad` (D7, cambio 2a).

Nace acá, con lo mínimo que el candado necesita para cargar el recurso
dentro de la sesión ya filtrada por RLS (D5): `None` si no existe o es de
otra administración (RLS ya lo filtró). El resto del dominio de complejos
(crearlos, editarlos, D6) es del cambio 3; este módulo nunca importa
`acceso` (D-021, frontera verificada en `test_fronteras_de_modulos.py`).
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ComplejoLeido:
    id: UUID
    administracion_id: UUID
    nombre: str


@dataclass(frozen=True)
class UnidadLeida:
    id: UUID
    administracion_id: UUID
    complejo_id: UUID
    nombre: str


def cargar_complejo(sesion: Session, complejo_id: UUID) -> ComplejoLeido | None:
    fila = sesion.execute(
        text("SELECT id, administracion_id, nombre FROM complejo WHERE id = :id"),
        {"id": str(complejo_id)},
    ).first()
    if fila is None:
        return None
    return ComplejoLeido(id=fila.id, administracion_id=fila.administracion_id, nombre=fila.nombre)


def cargar_unidad(sesion: Session, unidad_id: UUID) -> UnidadLeida | None:
    fila = sesion.execute(
        text("SELECT id, administracion_id, complejo_id, nombre FROM unidad WHERE id = :id"),
        {"id": str(unidad_id)},
    ).first()
    if fila is None:
        return None
    return UnidadLeida(
        id=fila.id,
        administracion_id=fila.administracion_id,
        complejo_id=fila.complejo_id,
        nombre=fila.nombre,
    )
