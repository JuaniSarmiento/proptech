"""PROVISORIO (rojo de la tarea 2.4): `aceptar_diferencias` todavía no acepta nada."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion


@dataclass(frozen=True)
class DiferenciaAceptada:
    unidad: str
    borrador: str
    control: str
    diferencia: str


@dataclass(frozen=True)
class AceptacionRegistrada:
    aceptacion_id: UUID
    diferencias: tuple[DiferenciaAceptada, ...]
    aceptada_por: UUID
    aceptada_en: datetime


@accion_sensible(Accion.ACEPTAR_DIFERENCIAS_DE_SALDOS)
def aceptar_diferencias(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    importacion_id: UUID,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> AceptacionRegistrada:
    return AceptacionRegistrada(uuid4(), (), identidad.persona_id, reloj())
