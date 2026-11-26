"""Alcance, permiso y pertenencia, en el orden de siempre (D7 del 2a): el edificio inexistente, de
otra administración o fuera de alcance da `NoEncontrado` (404); sin `emitir_libre_deuda` en él,
`SinPermiso` (403); una unidad que no es de ese edificio, `NoEncontrado`."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.complejos.aplicacion.errores import NoEncontrado
from proptech_core.complejos.aplicacion.lectura import UnidadLeida, cargar_complejo, cargar_unidad
from proptech_core.libre_deuda.aplicacion.errores import SinPermiso


@dataclass(frozen=True)
class UnidadAutorizada:
    unidad: UnidadLeida
    nombre_del_edificio: str


def unidad_autorizada(
    sesion: Session, identidad: Identidad, complejo_id: UUID, unidad_id: UUID
) -> UnidadAutorizada:
    """El tenant de la sesión (RLS) ya filtró la otra administración; se vuelve a mirar."""
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if (
        edificio is None
        or edificio.administracion_id != identidad.administracion_id
        or not alcanza(asignaciones, complejo_id)
    ):
        raise NoEncontrado()
    if not puede(asignaciones, Accion.EMITIR_LIBRE_DEUDA, complejo_id):
        raise SinPermiso(Accion.EMITIR_LIBRE_DEUDA.value)
    unidad = cargar_unidad(sesion, unidad_id)
    if unidad is None or unidad.complejo_id != complejo_id:
        raise NoEncontrado()
    return UnidadAutorizada(unidad, edificio.nombre)
