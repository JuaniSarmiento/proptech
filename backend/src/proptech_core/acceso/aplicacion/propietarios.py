"""Propietarios de una unidad dados de alta **sin invitar** (importación desde Excel, E3).

`dar_de_alta_vecino` crea la persona, la asigna y manda la invitación por Clerk. Importar un padrón
no puede mandar emails reales en una carga masiva sin revisión: la invitación sigue siendo la acción
existente, aparte. Estas dos funciones hacen sólo lo primero: no tocan `invitacion`, no auditan (la
importación audita una vez) y no renombran a quien ya existía.
"""

from __future__ import annotations

from collections.abc import Iterable
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


def nombres_de_propietarios(sesion: Session, complejo_id: UUID) -> dict[UUID, list[str]]:
    """Unidad → nombres de sus propietarios (asignación de vecino con vínculo `propietario`), en
    orden alfabético. Sólo el nombre: nunca inquilinos ni datos de contacto (10a, N03)."""
    filas = sesion.execute(
        text(
            "SELECT a.unidad_id, p.nombre FROM asignacion_rol a "
            "JOIN persona p ON p.id = a.persona_id "
            "WHERE a.rol = 'vecino' AND a.vinculo = 'propietario' AND a.complejo_id = :complejo"
        ),
        {"complejo": complejo_id},
    ).all()
    nombres: dict[UUID, list[str]] = {}
    for unidad_id, nombre in filas:
        nombres.setdefault(UUID(str(unidad_id)), []).append(str(nombre))
    return {unidad: sorted(lista) for unidad, lista in nombres.items()}


def vecinos_de_unidad_bloqueados(sesion: Session, *, unidad_id: UUID) -> dict[UUID, str]:
    """Persona → vínculo (`propietario` o `inquilino`) de cada asignación de vecino sobre la unidad,
    con las filas bloqueadas (`FOR UPDATE`): dos cambios de titular simultáneos de la misma unidad
    se serializan, y el segundo ve lo que dejó el primero (cambio de titular, H-030)."""
    filas = sesion.execute(
        text(
            "SELECT persona_id, vinculo FROM asignacion_rol "
            "WHERE rol = 'vecino' AND unidad_id = :unidad FOR UPDATE"
        ),
        {"unidad": unidad_id},
    ).all()
    return {UUID(str(persona)): str(vinculo) for persona, vinculo in filas}


def quitar_propietarios(sesion: Session, *, personas: Iterable[UUID], unidad_id: UUID) -> None:
    """Borra la asignación `vecino` / `propietario` de cada persona sobre la unidad. La persona, sus
    otras unidades y los inquilinos de ésta no se tocan."""
    for persona in personas:
        sesion.execute(
            text(
                "DELETE FROM asignacion_rol WHERE rol = 'vecino' AND vinculo = 'propietario' "
                "AND unidad_id = :unidad AND persona_id = :persona"
            ),
            {"unidad": unidad_id, "persona": persona},
        )


def nombres_de_personas(sesion: Session, persona_ids: Iterable[UUID]) -> dict[UUID, str]:
    """Persona → nombre, de las pedidas y sólo el nombre (cuenta del vendedor, H-033). Una persona
    de otra administración no aparece (RLS)."""
    ids = [str(p) for p in persona_ids]
    if not ids:
        return {}
    filas = sesion.execute(
        text("SELECT id, nombre FROM persona WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": ids},
    )
    return {UUID(str(fila.id)): str(fila.nombre) for fila in filas}
