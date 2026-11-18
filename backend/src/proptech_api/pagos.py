"""Pagos informados (change 8, D-163): subir el comprobante, informar el pago y leerlos (H-018).

Mismo orden que `liquidaciones.py`: cargar el edificio → 404 si no existe o no alcanza → 403 si no
tiene `informar_pago` ni `confirmar_pago_informado` ahí → el pedido (422) → las unidades (404) →
el número repetido (409). El cuerpo se valida a mano (después del 404 y del 403), no por FastAPI.
"""

from datetime import UTC, date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, Asignacion, alcanza
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.pagos.aplicacion import comprobantes, informar, lectura
from proptech_core.pagos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.pagos.aplicacion.permisos import puede_informar_o_ver, unidades_del_alcance
from proptech_core.pagos.dominio.comprobante import TAMANO_MAXIMO

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)


def hoy() -> date:
    """La fecha de hoy en Mendoza. Es una dependencia para que la aceptación la fije (L-090)."""
    return hoy_en_mendoza(lambda: datetime.now(UTC))


async def manejar_error_de_pagos(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, NoEncontrado):
        return JSONResponse(status_code=404, content={"detail": "no encontrado"})
    if isinstance(error, Conflicto):
        return JSONResponse(
            status_code=409,
            content={"detail": "conflicto", "campo": error.campo, "motivo": error.motivo},
        )
    if isinstance(error, EntradaInvalida):
        item = {"loc": [error.donde, error.campo], "msg": error.motivo, "type": "value_error"}
        return JSONResponse(status_code=422, content={"detail": [item]})
    raise TypeError("error de pagos inesperado")


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID
) -> list[Asignacion]:
    """404 si el edificio no existe o no alcanza; 403 sin `informar_pago` ni
    `confirmar_pago_informado` en él. Devuelve las asignaciones para repartir las unidades."""
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise HTTPException(status_code=404, detail="no encontrado")
    if not puede_informar_o_ver(asignaciones, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.INFORMAR_PAGO.value,
            },
        )
    return asignaciones


@router.post("/complejos/{complejo_id}/pagos/lectura", status_code=201)
def subir_comprobante(
    complejo_id: UUID,
    archivo: Annotated[UploadFile, File()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Guarda el comprobante (JPEG, PNG o PDF de hasta 10 MB, por sus primeros bytes). Se lee un
    byte de más del tope para saber que se pasó sin cargar un archivo enorme en memoria."""
    _edificio_autorizado(sesion, identidad, complejo_id)
    contenido = archivo.file.read(TAMANO_MAXIMO + 1)
    guardado = comprobantes.guardar_comprobante(
        sesion, identidad, complejo_id=complejo_id, contenido=contenido
    )
    sesion.commit()
    return guardado


@router.post("/complejos/{complejo_id}/pagos", status_code=201)
def informar_un_pago(
    complejo_id: UUID,
    cuerpo: Annotated[Any, Body()],
    fecha_de_hoy: date = Depends(hoy),
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    asignaciones = _edificio_autorizado(sesion, identidad, complejo_id)
    pago_id = informar.informar_pago(
        sesion,
        identidad,
        complejo_id=complejo_id,
        cuerpo=cuerpo,
        hoy=fecha_de_hoy,
        unidades_permitidas=unidades_del_alcance(asignaciones, complejo_id),
    )
    sesion.commit()
    return {"pago_id": str(pago_id), "estado": "informado"}


@router.get("/complejos/{complejo_id}/pagos")
def pagos_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    asignaciones = _edificio_autorizado(sesion, identidad, complejo_id)
    return lectura.listar_pagos(
        sesion, complejo_id=complejo_id, unidades=unidades_del_alcance(asignaciones, complejo_id)
    )


@router.get("/complejos/{complejo_id}/pagos/{pago_id}")
def pago_informado(
    complejo_id: UUID,
    pago_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    asignaciones = _edificio_autorizado(sesion, identidad, complejo_id)
    pago = lectura.leer_pago(
        sesion,
        complejo_id=complejo_id,
        pago_id=pago_id,
        unidades=unidades_del_alcance(asignaciones, complejo_id),
    )
    if pago is None:
        raise NoEncontrado
    return pago
