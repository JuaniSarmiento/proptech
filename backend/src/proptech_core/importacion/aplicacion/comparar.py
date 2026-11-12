"""PROVISORIO (rojo de la tarea 2.3): `comparar_borrador` todavía no lee el borrador."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.importacion.aplicacion.aceptar import AceptacionRegistrada
from proptech_core.importacion.dominio.comparacion import UnidadComparada


@dataclass(frozen=True)
class ComparacionDelBorrador:
    importacion_id: UUID
    unidades: tuple[UnidadComparada, ...]
    total_borrador: Dinero
    total_control: Dinero
    unidades_con_diferencia: int
    requiere_aceptacion: bool
    aceptacion: AceptacionRegistrada | None


def comparar_borrador(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID
) -> ComparacionDelBorrador:
    return ComparacionDelBorrador(uuid4(), (), Dinero("0.00"), Dinero("0.00"), 0, False, None)
