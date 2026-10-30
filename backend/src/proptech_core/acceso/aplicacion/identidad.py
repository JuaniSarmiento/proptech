"""D2/D3: directorio mínimo por identidad y luego sesión del tenant elegido."""

import hashlib
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import abrir_sesion, abrir_sesion_por_identidad

_logger = logging.getLogger(__name__)


class SinAcceso(Exception):
    """Token válido sin asignaciones en ninguna administración vinculada."""


class IdentidadNoDisponible(Exception):
    """Rechazo de elección de una identidad con acceso en otra administración."""


def personas_vinculadas(fabrica: sessionmaker[Session], sub: str) -> list[Identidad]:
    with abrir_sesion_por_identidad(fabrica, sub) as sesion:
        filas = sesion.execute(
            text("SELECT id, administracion_id FROM persona WHERE clerk_usuario_id = :sub"),
            {"sub": sub},
        ).all()
    return [Identidad(f.administracion_id, f.id) for f in filas]


def resolver(
    fabrica: sessionmaker[Session], sub: str, selector: str | None, *, request_id: UUID
) -> Identidad:
    personas = personas_vinculadas(fabrica, sub)
    if not personas:
        _logger.info(
            "ingreso_sin_vinculo",
            extra={"sub_resumen": hashlib.sha256(sub.encode()).hexdigest()[:12]},
        )
        raise SinAcceso

    # Elegir primero: sólo una persona elegida puede dejar ingreso_fallido.
    identidad = None
    if selector is None:
        if len(personas) == 1:
            identidad = personas[0]
    else:
        try:
            administracion = UUID(selector)
        except ValueError:
            pass
        else:
            identidad = next((p for p in personas if p.administracion_id == administracion), None)
    if identidad is not None:
        with abrir_sesion(fabrica, identidad.administracion_id) as sesion:
            if cargar_asignaciones(sesion, identidad.persona_id):
                return identidad
            registrar(
                sesion,
                identidad,
                EventoDeAcceso.INGRESO_FALLIDO,
                entidad="persona",
                entidad_id=identidad.persona_id,
                request_id=request_id,
                detalle={"motivo": "sin_asignacion"},
            )
            sesion.commit()

    # El selector nunca autoriza una lectura: sólo se abren tenants vinculados.
    for persona in personas:
        with abrir_sesion(fabrica, persona.administracion_id) as sesion:
            if cargar_asignaciones(sesion, persona.persona_id):
                raise IdentidadNoDisponible
    raise SinAcceso
