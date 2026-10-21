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


class IdentidadNoDisponible(Exception):
    """Sin detalles públicos: todos los rechazos se traducen al mismo 401."""


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
            extra={
                "sub_resumen": hashlib.sha256(sub.encode()).hexdigest()[:12],
            },
        )
        raise IdentidadNoDisponible
    if selector is None:
        if len(personas) != 1:
            raise IdentidadNoDisponible
        identidad = personas[0]
    else:
        try:
            administracion = UUID(selector)
        except ValueError:
            raise IdentidadNoDisponible from None
        candidatas = [p for p in personas if p.administracion_id == administracion]
        if not candidatas:
            raise IdentidadNoDisponible
        identidad = candidatas[0]
    with abrir_sesion(fabrica, identidad.administracion_id) as sesion:
        if not cargar_asignaciones(sesion, identidad.persona_id):
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
            raise IdentidadNoDisponible
    return identidad
