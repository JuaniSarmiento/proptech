"""D5: la API compone alcance de complejos y permiso de acceso, antes del cuerpo."""

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, Field, ValidationError
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.aplicacion.datos_de_usuario import email_valido, nombre_valido
from proptech_core.acceso.aplicacion.usuarios import (
    ConflictoDeAcceso,
    encolar_alta,
    invitar_personal,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.lectura import cargar_complejo

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)
PERMISO = Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS


class CuerpoPersonal(CuerpoDeAlta):
    nombre: Annotated[str, AfterValidator(lambda valor: nombre_valido(valor))]
    email: Annotated[str, AfterValidator(email_valido)]
    rol: Literal["administrador", "contador", "auxiliar", "consejo"]
    alcance: Literal["principal", "edificio"]
    complejo_id: Annotated[UUID, Field(strict=False)] | None = None


def autorizar(sesion: Session, identidad: Identidad, complejo_id: UUID | None = None) -> None:
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if complejo_id is not None:
        if cargar_complejo(sesion, complejo_id) is None or not alcanza(asignaciones, complejo_id):
            raise HTTPException(404, detail="no encontrado")
    if not puede(asignaciones, PERMISO, complejo_id):
        raise HTTPException(
            403, detail={"detalle": "sin_permiso", "permiso_faltante": PERMISO.value}
        )


def campo_invalido(campo: str) -> None:
    raise RequestValidationError(
        [{"type": "value_error", "loc": ("body", campo), "msg": "valor inválido"}]
    )


async def manejar_conflicto(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, ConflictoDeAcceso):
        raise TypeError("error de acceso inesperado")
    return JSONResponse(status_code=409, content={"detail": "conflicto", "campo": error.campo})


@router.post("/personal/invitaciones", status_code=201)
async def invitar(
    request: Request,
    cuerpo: Annotated[Any, Body()] = None,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str | None]:
    complejo = cuerpo.get("complejo_id") if isinstance(cuerpo, dict) else None
    if complejo is not None:
        try:
            complejo = UUID(str(complejo))
        except ValueError:
            # Un UUID mal formado es un error de cuerpo; se valida entero tras el permiso.
            complejo = None
    autorizar(sesion, identidad, complejo)
    try:
        datos = CuerpoPersonal.model_validate(cuerpo)
    except ValidationError as error:
        raise RequestValidationError(
            [dict(e, loc=("body", *e["loc"])) for e in error.errors()]
        ) from None
    if (datos.alcance == "edificio") != (datos.complejo_id is not None) or (
        datos.rol in {"auxiliar", "consejo"} and datos.alcance == "principal"
    ):
        campo_invalido("alcance")
    request_id = UUID(request_id_actual.get() or "")
    alta = invitar_personal(
        sesion,
        identidad,
        nombre=datos.nombre,
        email=datos.email,
        rol=datos.rol,
        alcance=datos.alcance,
        complejo_id=datos.complejo_id,
        parametros=request.app.state.parametros,
        configuracion=request.app.state.configuracion,
        request_id=request_id,
    )
    sesion.commit()
    await encolar_alta(request.app.state.cola, identidad, alta, request_id)
    return {
        "persona_id": str(alta.persona_id),
        "asignacion_id": str(alta.asignacion_id),
        "invitacion_id": str(alta.invitacion_id) if alta.invitacion_id else None,
    }
