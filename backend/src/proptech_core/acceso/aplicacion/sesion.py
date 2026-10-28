"""D3/D8: nombres bajo cada tenant y registro explícito de ingreso."""

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.aplicacion.identidad import SinAcceso, personas_vinculadas
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import abrir_sesion


def consultar(fabrica: sessionmaker[Session], sub: str) -> dict[str, Any]:
    personas = personas_vinculadas(fabrica, sub)
    if not personas:
        raise SinAcceso
    administraciones = []
    nombre = ""
    for identidad in personas:
        with abrir_sesion(fabrica, identidad.administracion_id) as sesion:
            if not cargar_asignaciones(sesion, identidad.persona_id):
                continue
            persona = sesion.execute(
                text("SELECT nombre FROM persona WHERE id = :id"), {"id": identidad.persona_id}
            ).scalar_one()
            administracion = sesion.execute(
                text("SELECT nombre FROM administracion WHERE id = :id"),
                {"id": identidad.administracion_id},
            ).scalar_one()
            if not nombre:
                nombre = persona
            administraciones.append(
                {"id": str(identidad.administracion_id), "nombre": administracion}
            )
    if not administraciones:
        raise SinAcceso
    return {"persona": {"nombre": nombre}, "administraciones": administraciones}


def registrar_ingreso(sesion: Session, identidad: Identidad, request_id: UUID) -> None:
    with sesion.begin():
        registrar(
            sesion,
            identidad,
            EventoDeAcceso.INGRESO_EXITOSO,
            entidad="persona",
            entidad_id=identidad.persona_id,
            request_id=request_id,
        )
