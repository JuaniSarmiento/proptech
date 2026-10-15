"""Los tres endpoints mínimos del candado (D7, cambio 2a, tarea 4.2): ver un
complejo, ver una unidad, asignar un edificio a una persona.

Acá sólo el cableado de identidad y tenant (D7): cargan por id dentro de la
sesión ya filtrada por RLS (D5) y devuelven 404 si no existe. El alcance por
edificio (D6, "no alcanza" aunque exista) y el permiso por acción de D-096
todavía no están — los suma la tarea 5.x, envolviendo estos mismos
endpoints. Por eso el 404 de acá es parcial: cubre "no existe o es de otra
administración" (ya lo filtra RLS), no "existe pero no te alcanza".
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_api.acceso import identidad_actual, sesion_con_tenant
from proptech_core.acceso.dominio.identidad import Identidad

router = APIRouter(prefix="/api")


@router.get("/complejos/{complejo_id}")
def ver_complejo(complejo_id: UUID, sesion: Session = Depends(sesion_con_tenant)) -> dict[str, str]:
    fila = sesion.execute(
        text("SELECT id, administracion_id, nombre FROM complejo WHERE id = :id"),
        {"id": str(complejo_id)},
    ).first()
    if fila is None:
        raise HTTPException(status_code=404)
    return {
        "id": str(fila.id),
        "administracion_id": str(fila.administracion_id),
        "nombre": fila.nombre,
    }


@router.get("/unidades/{unidad_id}")
def ver_unidad(unidad_id: UUID, sesion: Session = Depends(sesion_con_tenant)) -> dict[str, str]:
    fila = sesion.execute(
        text("SELECT id, administracion_id, complejo_id, nombre FROM unidad WHERE id = :id"),
        {"id": str(unidad_id)},
    ).first()
    if fila is None:
        raise HTTPException(status_code=404)
    return {
        "id": str(fila.id),
        "administracion_id": str(fila.administracion_id),
        "complejo_id": str(fila.complejo_id),
        "nombre": fila.nombre,
    }


class CuerpoAsignacion(BaseModel):
    persona_id: UUID
    rol: str
    nivel: str | None = None
    # Se acepta para que un cuerpo que lo manda no explote con un campo
    # desconocido (422), pero se ignora a propósito (D7, D4): el tenant de
    # la fila sale siempre de la identidad, nunca de un campo del cuerpo.
    administracion_id: UUID | None = None


@router.post("/complejos/{complejo_id}/asignaciones", status_code=201)
def asignar_complejo(
    complejo_id: UUID,
    cuerpo: CuerpoAsignacion,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    fila = sesion.execute(
        text(
            "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, complejo_id, nivel) "
            "VALUES (:administracion_id, :persona_id, :rol, :complejo_id, :nivel) "
            "RETURNING id"
        ),
        {
            # Siempre de la identidad (D7): nunca de `cuerpo.administracion_id`.
            "administracion_id": str(identidad.administracion_id),
            "persona_id": str(cuerpo.persona_id),
            "rol": cuerpo.rol,
            "complejo_id": str(complejo_id),
            "nivel": cuerpo.nivel,
        },
    ).one()
    sesion.commit()
    return {"id": str(fila.id)}
