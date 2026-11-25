"""El cambio de titular de una unidad (4d, H-030, R32, D-168): registrarlo y listar los de ella.

Los dos casos de uso autorizan solos, en el orden de D7: el edificio que no existe o no alcanza, o
la unidad que no es de él, da 404; sin `registrar_cambio_de_titular` (que también cubre leer), 403;
la entrada que no sirve, 422. `NoEncontrado` y `EntradaInvalida` los traduce el manejador de
`complejos`.
En H-030 sólo se aceptan las dos opciones de R32 en su valor por defecto; las otras las habilitan
H-031 y H-032.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, Field
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_api.morosidad import hoy
from proptech_core.acceso.aplicacion.datos_de_usuario import email_valido, nombre_valido
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.titularidad.aplicacion.errores import SinPermiso
from proptech_core.titularidad.aplicacion.lectura import CambioDeTitular, listar_cambios
from proptech_core.titularidad.aplicacion.registrar import (
    CompradorPedido,
    registrar_cambio_de_titular,
)

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


async def manejar_sin_permiso(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, SinPermiso):
        raise TypeError(f"manejar_sin_permiso recibió un error inesperado: {type(error)!r}")
    return JSONResponse(
        status_code=403,
        content={
            "detail": {
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": error.permiso_faltante,
            }
        },
    )


def _nombre(valor: str) -> str:
    recortado = nombre_valido(valor)
    if not 1 <= len(recortado) <= 80:
        raise ValueError("el nombre debe tener de 1 a 80 caracteres")
    return recortado


class CuerpoComprador(CuerpoDeAlta):
    nombre: Annotated[str, AfterValidator(_nombre)]
    email: Annotated[str, AfterValidator(email_valido)] | None = None


class CuerpoCambioDeTitular(CuerpoDeAlta):
    #: Texto `AAAA-MM-DD`: el caso de uso lo lee, para que su 422 llegue después del 404 y del 403.
    fecha: str
    vendedores: list[Annotated[UUID, Field(strict=False)]]
    compradores: list[CuerpoComprador]
    #: H-031 y H-032 habilitan los otros valores.
    expensa_del_mes: Literal["entera"] = "entera"
    deuda_previa: Literal["en_la_unidad"] = "en_la_unidad"


def _como_json(cambio: CambioDeTitular, *, con_aviso: bool) -> dict[str, Any]:
    respuesta: dict[str, Any] = {
        "id": str(cambio.id),
        "unidad_id": str(cambio.unidad_id),
        "fecha": cambio.fecha.isoformat(),
        "vendedores": [str(v) for v in cambio.vendedores],
        "compradores": [
            {"nombre": c.nombre, "email": c.email, "persona_id": str(c.persona_id)}
            for c in cambio.compradores
        ],
        "expensa_del_mes": cambio.expensa_del_mes,
        "deuda_previa": cambio.deuda_previa,
        "registrado_por": str(cambio.registrado_por),
        "registrado_en": cambio.registrado_en.isoformat(),
    }
    if con_aviso:
        respuesta["aviso"] = None if cambio.aviso is None else {"deuda": cambio.aviso.a_texto()}
    return respuesta


@router.post("/complejos/{complejo_id}/unidades/{unidad_id}/cambios-de-titular", status_code=201)
def registrar(
    complejo_id: UUID,
    unidad_id: UUID,
    cuerpo: CuerpoCambioDeTitular,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> dict[str, Any]:
    """Los vendedores dejan de ser propietarios de la unidad y los compradores lo pasan a ser; si la
    unidad debe, `aviso` trae el monto (nunca bloquea)."""
    cambio = registrar_cambio_de_titular(
        sesion,
        identidad,
        complejo_id=complejo_id,
        unidad_id=unidad_id,
        fecha=cuerpo.fecha,
        vendedores=cuerpo.vendedores,
        compradores=[CompradorPedido(c.nombre, c.email) for c in cuerpo.compradores],
        expensa_del_mes=cuerpo.expensa_del_mes,
        deuda_previa=cuerpo.deuda_previa,
        hoy=fecha_de_hoy,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return _como_json(cambio, con_aviso=True)


@router.get("/complejos/{complejo_id}/unidades/{unidad_id}/cambios-de-titular")
def listar(
    complejo_id: UUID,
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    cambios = listar_cambios(sesion, identidad, complejo_id=complejo_id, unidad_id=unidad_id)
    return [_como_json(c, con_aviso=False) for c in cambios]
