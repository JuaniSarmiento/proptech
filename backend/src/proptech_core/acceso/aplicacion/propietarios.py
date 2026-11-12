"""Propietarios de una unidad dados de alta **sin invitar** (importación desde Excel, E3).

`dar_de_alta_vecino` crea la persona, la asigna y manda la invitación por Clerk. Importar un padrón
no puede mandar emails reales en una carga masiva sin revisión: la invitación sigue siendo la acción
existente, aparte. Estas dos funciones hacen sólo lo primero: no tocan `invitacion`, no auditan (la
importación audita una vez) y no renombran a quien ya existía.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad


@dataclass(frozen=True)
class PersonaAsegurada:
    persona_id: UUID
    #: `True` si la persona no existía en la administración antes de esta llamada.
    creada: bool


def asegurar_persona(
    sesion: Session, identidad: Identidad, *, nombre: str, email: str | None
) -> PersonaAsegurada:
    """Crea la persona, o reusa la que ya tiene ese email en la administración (sin cambiarle el
    nombre). Sin email siempre crea una nueva. El `ON CONFLICT` cubre la carrera con otra alta del
    mismo email en otro edificio: nunca un 500 por el único."""
    if email is not None:
        existente = sesion.execute(
            text("SELECT id FROM persona WHERE administracion_id = :admin AND email = :email"),
            {"admin": identidad.administracion_id, "email": email},
        ).scalar_one_or_none()
        if existente is not None:
            return PersonaAsegurada(existente, creada=False)
    nueva = sesion.execute(
        text(
            "INSERT INTO persona (administracion_id, nombre, email) "
            "VALUES (:admin, :nombre, :email) "
            "ON CONFLICT (administracion_id, email) DO NOTHING RETURNING id"
        ),
        {"admin": identidad.administracion_id, "nombre": nombre, "email": email},
    ).scalar_one_or_none()
    if nueva is not None:
        return PersonaAsegurada(nueva, creada=True)
    ganadora = sesion.execute(
        text("SELECT id FROM persona WHERE administracion_id = :admin AND email = :email"),
        {"admin": identidad.administracion_id, "email": email},
    ).scalar_one()
    return PersonaAsegurada(ganadora, creada=False)


def asignar_propietario(
    sesion: Session,
    identidad: Identidad,
    *,
    persona_id: UUID,
    complejo_id: UUID,
    unidad_id: UUID,
) -> UUID:
    """La asignación `vecino` / `propietario` de la persona sobre la unidad (sin invitación)."""
    return UUID(
        str(
            sesion.execute(
                text(
                    "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, "
                    "unidad_id, vinculo) VALUES (:admin, :persona, 'vecino', :complejo, :unidad, "
                    "'propietario') RETURNING id"
                ),
                {
                    "admin": identidad.administracion_id,
                    "persona": persona_id,
                    "complejo": complejo_id,
                    "unidad": unidad_id,
                },
            ).scalar_one()
        )
    )
