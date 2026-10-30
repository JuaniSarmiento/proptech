"""Vínculo sin invitación, exclusivo del ejemplo de desarrollo (E5/E6)."""

from typing import Any, cast
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

#: Ids fijos de la administración y de la persona de ejemplo (D9 del 3a, D1
#: de `acceso-de-desarrollo`): nunca generados, para que `cargar()` compare
#: contra la misma fila en cada corrida en vez de crear una fila nueva.
ADMINISTRACION_EJEMPLO_ID = UUID("00000000-0000-4000-8000-0000000000e0")
PERSONA_SUPER_ADMIN_EJEMPLO_ID = UUID("00000000-0000-4000-8000-0000000000e1")
_MENSAJE_CUENTA_AJENA = "esa cuenta ya está vinculada a otra persona del ejemplo"


class VinculacionDeDesarrolloNoDisponible(Exception):
    """Rechazo propio sin identificadores ni parámetros del driver."""


def vincular(sesion: Session, administracion_id: UUID, persona_id: UUID, sub: str) -> str:
    """El caller conserva la transacción y el tenant; sólo acepta el ejemplo."""
    if (
        administracion_id != ADMINISTRACION_EJEMPLO_ID
        or persona_id != PERSONA_SUPER_ADMIN_EJEMPLO_ID
    ):
        raise VinculacionDeDesarrolloNoDisponible("sólo se puede vincular la persona del ejemplo")
    ajena = sesion.execute(
        text("SELECT id FROM persona WHERE clerk_usuario_id = :sub AND id <> :persona LIMIT 1"),
        {"sub": sub, "persona": persona_id},
    ).first()
    if ajena is not None:
        raise VinculacionDeDesarrolloNoDisponible(_MENSAJE_CUENTA_AJENA)
    anterior = sesion.execute(
        text("SELECT clerk_usuario_id FROM persona WHERE id = :persona"),
        {"persona": persona_id},
    ).scalar_one()
    if anterior == sub:
        # B-1 (rompedor, vuelta 1): el id ya es el mismo -- la spec pide
        # "no hace nada / sin escribir". El UPDATE condicional de abajo
        # coincide igual cuando el id no cambia y Postgres escribe una
        # versión nueva de la fila (visible en `xmin`) aunque el valor
        # final sea idéntico. Devolver antes evita esa escritura.
        return "ya estaba vinculado"
    try:
        resultado = cast(
            CursorResult[Any],
            sesion.execute(
                text(
                    "UPDATE persona SET clerk_usuario_id = :sub WHERE id = :persona "
                    "AND (clerk_usuario_id IS NULL OR clerk_usuario_id = :sub)"
                ),
                {"sub": sub, "persona": persona_id},
            ),
        )
    except IntegrityError as error:
        if (
            isinstance(error.orig, UniqueViolation)
            and error.orig.diag.constraint_name == "uq_persona_clerk_administracion"
        ):
            raise VinculacionDeDesarrolloNoDisponible(_MENSAJE_CUENTA_AJENA) from None
        raise
    if resultado.rowcount != 1:
        raise VinculacionDeDesarrolloNoDisponible("el ejemplo ya está vinculado a otra cuenta")
    return "ya estaba vinculado" if anterior == sub else "vinculado"
