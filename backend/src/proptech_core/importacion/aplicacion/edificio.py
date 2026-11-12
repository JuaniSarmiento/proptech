"""Alcance y permiso sobre el edificio, en el orden de siempre (D7 del 2a), para los casos de uso de
la importación: el edificio inexistente, de otra administración o fuera de alcance no existe
(`NoEncontrado`, 404); sin el permiso es `SinPermiso` (403)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.complejos.aplicacion.errores import NoEncontrado
from proptech_core.complejos.aplicacion.lectura import ComplejoLeido, cargar_complejo
from proptech_core.importacion.aplicacion.errores import SinPermiso


def edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> ComplejoLeido:
    """El tenant de la sesión (RLS) ya filtró la otra administración; se vuelve a mirar."""
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if (
        edificio is None
        or edificio.administracion_id != identidad.administracion_id
        or not alcanza(asignaciones, complejo_id)
    ):
        raise NoEncontrado()
    if not puede(asignaciones, accion, complejo_id):
        raise SinPermiso(accion.value)
    return edificio
