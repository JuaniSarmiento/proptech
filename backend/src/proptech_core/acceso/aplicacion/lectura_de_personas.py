"""Lecturas mínimas de personas para otros módulos (H-035, 4d): sólo id y nombre, nunca el email, el
teléfono ni el documento. El tenant de la sesión (RLS) ya filtra la administración; se vuelve a
filtrar por ella."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad


@dataclass(frozen=True)
class PersonaConNombre:
    persona_id: UUID
    nombre: str


def propietarios_de_unidad(
    sesion: Session, identidad: Identidad, *, unidad_id: UUID
) -> list[PersonaConNombre]:
    """Los propietarios actuales de la unidad (asignación `vecino` con vínculo `propietario`), por
    nombre; una persona con dos asignaciones iguales aparece una sola vez."""
    filas = sesion.execute(
        text(
            "SELECT DISTINCT p.id, p.nombre FROM asignacion_rol a "
            "JOIN persona p ON p.id = a.persona_id AND p.administracion_id = a.administracion_id "
            "WHERE a.unidad_id = :unidad AND a.rol = 'vecino' AND a.vinculo = 'propietario' "
            "AND a.administracion_id = :admin ORDER BY p.nombre, p.id"
        ),
        {"unidad": unidad_id, "admin": identidad.administracion_id},
    ).all()
    return [PersonaConNombre(f.id, f.nombre) for f in filas]


def nombres_de_personas(
    sesion: Session, identidad: Identidad, *, persona_ids: Iterable[UUID]
) -> dict[UUID, str]:
    ids = list(set(persona_ids))
    if not ids:
        return {}
    filas = sesion.execute(
        text(
            "SELECT id, nombre FROM persona "
            "WHERE administracion_id = :admin AND id = ANY(:ids)"
        ),
        {"admin": identidad.administracion_id, "ids": ids},
    ).all()
    return {f.id: f.nombre for f in filas}
