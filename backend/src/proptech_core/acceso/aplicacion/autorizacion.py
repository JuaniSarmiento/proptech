"""Composición de la matriz de D-096 con la base (D7, cambio 2a).

Carga las asignaciones de la persona (ya filtradas por RLS) para que la API
llame `alcanza`/`puede` (`acceso.dominio.permisos`) sin escribir SQL. Nunca
importa `complejos` (D-021): la API, que compone los dos módulos, es quien
sabe a qué complejo pertenece una unidad.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.permisos import Asignacion, Rol


def existe_persona(sesion: Session, persona_id: UUID) -> bool:
    """Si `persona_id` es de otra administración, RLS ya lo filtra: da
    `False`, igual que si no existiera (D7, L-017: el id de otra
    administración siempre es un UUID real y existente en la base, nunca
    un texto que FastAPI ya rechaza con 422)."""
    fila = sesion.execute(
        text("SELECT 1 FROM persona WHERE id = :persona_id"), {"persona_id": str(persona_id)}
    ).first()
    return fila is not None


def cargar_asignaciones(sesion: Session, persona_id: UUID) -> list[Asignacion]:
    filas = sesion.execute(
        text(
            "SELECT rol, complejo_id, unidad_id FROM asignacion_rol WHERE persona_id = :persona_id"
        ),
        {"persona_id": str(persona_id)},
    ).all()
    return [
        Asignacion(
            rol=Rol(fila.rol),
            complejo_id=fila.complejo_id,
            unidad_id=fila.unidad_id,
            # 4.1 leerá el vínculo real; los vecinos existentes de 0016 son propietarios.
            vinculo="propietario" if fila.rol == "vecino" else None,
        )
        for fila in filas
    ]
