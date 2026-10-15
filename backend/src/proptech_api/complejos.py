"""Los tres endpoints mínimos del candado (D7, cambio 2a, tareas 4.2 y 5.x):
ver un complejo, ver una unidad, asignar un edificio a una persona.

Compone `complejos.aplicacion` (cargar) y `acceso.aplicacion` + `acceso.
dominio.permisos` (autorizar, D-096): nunca al revés (D-021, frontera
verificada en `test_fronteras_de_modulos.py`). El orden de cada endpoint es
siempre el de D7: cargar el recurso en la sesión con tenant (ya filtrada
por RLS) → si no existe o no alcanza, 404 (`_no_encontrado()`, siempre la
misma respuesta, para no filtrar cuál de los dos pasó, L-017) → si no
puede, 403 con `permiso_faltante` (tarea 5.3).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from proptech_api.acceso import identidad_actual, sesion_con_tenant
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones, existe_persona
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.escritura import asignar_complejo_a_persona
from proptech_core.complejos.aplicacion.lectura import cargar_complejo, cargar_unidad

router = APIRouter(prefix="/api")


def _no_encontrado() -> HTTPException:
    """Una sola función para "no existe" y "no alcanza" (L-017): las dos
    tienen que dar exactamente la misma respuesta, nunca una variación que
    delate cuál de las dos pasó."""
    return HTTPException(status_code=404, detail="no encontrado")


@router.get("/complejos/{complejo_id}")
def ver_complejo(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None:
        raise _no_encontrado()
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    return {
        "id": str(complejo.id),
        "administracion_id": str(complejo.administracion_id),
        "nombre": complejo.nombre,
    }


@router.get("/unidades/{unidad_id}")
def ver_unidad(
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    unidad = cargar_unidad(sesion, unidad_id)
    if unidad is None:
        raise _no_encontrado()
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not alcanza(asignaciones, unidad.complejo_id, unidad_id):
        raise _no_encontrado()
    return {
        "id": str(unidad.id),
        "administracion_id": str(unidad.administracion_id),
        "complejo_id": str(unidad.complejo_id),
        "nombre": unidad.nombre,
    }


class CuerpoAsignacion(BaseModel):
    persona_id: UUID
    rol: str
    nivel: str | None = None
    # Se acepta para que un cuerpo que lo manda no explote con un campo
    # desconocido (422), pero se ignora a propósito (D7, D4): el tenant de
    # la fila sale siempre de la identidad, nunca de un campo del cuerpo.
    administracion_id: UUID | None = None


#: La acción de D-096 que este endpoint autoriza (D9: el mismo nombre que
#: va a quedar registrado en la auditoría, tarea 6.x).
_ACCION = Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS


@router.post("/complejos/{complejo_id}/asignaciones", status_code=201)
def asignar_complejo(
    complejo_id: UUID,
    cuerpo: CuerpoAsignacion,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None:
        raise _no_encontrado()
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if not alcanza(asignaciones, complejo_id):
        raise _no_encontrado()
    if not puede(asignaciones, _ACCION, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={"detalle": "sin_permiso", "permiso_faltante": _ACCION.value},
        )
    # La persona destino (del cuerpo, no del path): recién después del
    # permiso, para no revelar si existe antes de confirmar que quien pide
    # puede hacer esta acción en este complejo.
    if not existe_persona(sesion, cuerpo.persona_id):
        raise _no_encontrado()

    # El request_id lo fija el middleware (D8): siempre un UUID canónico
    # dentro de un pedido real (`seguimiento.validar_request_id`).
    request_id = UUID(request_id_actual.get() or "")
    nueva_id = asignar_complejo_a_persona(
        sesion,
        identidad,
        complejo_id=complejo_id,
        persona_id=cuerpo.persona_id,
        rol=cuerpo.rol,
        nivel=cuerpo.nivel,
        request_id=request_id,
    )
    sesion.commit()
    return {"id": str(nueva_id)}
