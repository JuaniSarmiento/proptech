"""Correcciones del libro: valida el borde y confirma la unidad transaccional (D9/D10)."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.complejos import _edificio_autorizado
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_api.errores import RESPUESTAS_DE_ERROR
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion, corregir
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    TemporalmenteNoDisponible,
)

_UUIDDeCuerpo = Annotated[UUID, Field(strict=False)]


def _positivo(importe: Dinero) -> Dinero:
    if importe <= Dinero("0.00"):
        raise ValueError("el importe debe ser positivo")
    return importe


class _Correccion(CuerpoDeAlta):
    operacion_id: _UUIDDeCuerpo
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_valido(cls, motivo: str) -> str:
        motivo = recortado_sin_control(motivo)
        if len(motivo) > 500:
            raise ValueError("el motivo debe tener de 1 a 500 caracteres")
        return motivo


class CuerpoContraAsiento(_Correccion):
    forma: Literal["contra_asiento"]
    movimiento_id: _UUIDDeCuerpo


class CuerpoCredito(_Correccion):
    forma: Literal["credito"]
    obligacion_id: _UUIDDeCuerpo
    importe: Annotated[Dinero, AfterValidator(_positivo)]


class CorreccionCreada(BaseModel):
    movimiento_id: UUID


router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


@router.post(
    "/complejos/{complejo_id}/correcciones",
    status_code=201,
    response_model=CorreccionCreada,
    responses=RESPUESTAS_DE_ERROR,
)
def crear_correccion(
    complejo_id: UUID,
    cuerpo: Annotated[CuerpoContraAsiento | CuerpoCredito, Field(discriminator="forma")],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> CorreccionCreada:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CORREGIR_MOVIMIENTO)
    pedido = PedidoDeCorreccion(
        cuerpo.forma,
        cuerpo.operacion_id,
        cuerpo.motivo,
        movimiento_id=cuerpo.movimiento_id if isinstance(cuerpo, CuerpoContraAsiento) else None,
        obligacion_id=cuerpo.obligacion_id if isinstance(cuerpo, CuerpoCredito) else None,
        importe=cuerpo.importe if isinstance(cuerpo, CuerpoCredito) else None,
    )
    resultado = corregir(
        sesion,
        identidad,
        complejo_id=complejo_id,
        pedido=pedido,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return CorreccionCreada(movimiento_id=resultado)


async def manejar_error_del_libro(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, NoEncontrado):
        return JSONResponse(status_code=404, content={"detail": "no encontrado"})
    if isinstance(error, Conflicto):
        return JSONResponse(status_code=409, content={"detail": "conflicto", "campo": error.campo})
    if isinstance(error, EntradaInvalida):
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": ["body", *error.campo.split(".")],
                        "msg": error.motivo,
                        "type": "value_error",
                    }
                ]
            },
        )
    if isinstance(error, TemporalmenteNoDisponible):
        return JSONResponse(status_code=503, content={"detail": "temporalmente no disponible"})
    raise TypeError("error del libro inesperado")
