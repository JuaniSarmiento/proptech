"""Pagos informados (change 8, D-163): subir el comprobante, informar el pago y leerlos (H-018),
confirmarlo o rechazarlo (H-020).

Mismo orden que `liquidaciones.py`: cargar el edificio → 404 si no existe o no alcanza → 403 si no
tiene `informar_pago` ni `confirmar_pago_informado` ahí → el pedido (422) → las unidades (404) →
el número repetido (409). El cuerpo se valida a mano (después del 404 y del 403), no por FastAPI.
Confirmar y rechazar piden `confirmar_pago_informado` (403 si no) → el pago del edificio (404) →
el motivo (422) → el estado (409). Revertir (H-022) y reimputar (H-023) piden
`revertir_o_reimputar_pago`, con el mismo orden.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, Asignacion, alcanza, puede
from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.configuracion import ConfiguracionInvalida
from proptech_core.compartido.enlaces import EnlaceVencido
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.pagos.adaptadores.openrouter import LectorOpenRouter
from proptech_core.pagos.aplicacion import comprobantes, enlaces, informar, lectura, resolver
from proptech_core.pagos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.pagos.aplicacion.permisos import (
    es_personal_de_pagos,
    puede_informar_o_ver,
    unidades_del_alcance,
)
from proptech_core.pagos.dominio.comprobante import TAMANO_MAXIMO
from proptech_core.pagos.puertos import LectorDeComprobantes

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)
#: La descarga del comprobante (H-024): pública por diseño. El token firmado ES la autorización
#: (E11), así que no pasa por identidad ni por tenant: el tenant sale del token verificado.
router_de_descarga = APIRouter(prefix="/api")
#: Cuánto dura un enlace de descarga del comprobante (D-070).
VIGENCIA_DEL_ENLACE = timedelta(minutes=15)


def hoy() -> date:
    """La fecha de hoy en Mendoza. Es una dependencia para que la aceptación la fije (L-090)."""
    return hoy_en_mendoza(lambda: datetime.now(UTC))


def lector(request: Request) -> LectorDeComprobantes | None:
    """El lector de comprobantes con IA (OpenRouter), o `None` sin clave o sin modelo (`sin_ia`).
    Es una dependencia para que la aceptación ponga un lector falso."""
    configuracion = request.app.state.configuracion
    if (
        configuracion.proptech_openrouter_api_key is None
        or not configuracion.proptech_openrouter_modelo
    ):
        return None
    return LectorOpenRouter(
        configuracion.proptech_openrouter_api_key.get_secret_value(),
        configuracion.proptech_openrouter_modelo,
    )


def tope_de_lectura() -> float:
    """Los segundos que se espera a la IA antes de dar la lectura por fallida."""
    return comprobantes.TOPE_DE_LECTURA_S


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


def _edificio_de_quien_confirma(sesion: Session, identidad: Identidad, complejo_id: UUID) -> None:
    """404 si el edificio no existe o no alcanza; 403 sin `confirmar_pago_informado` en él."""
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise HTTPException(status_code=404, detail="no encontrado")
    if not es_personal_de_pagos(asignaciones, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.CONFIRMAR_PAGO_INFORMADO.value,
            },
        )


def _edificio_de_quien_revierte(sesion: Session, identidad: Identidad, complejo_id: UUID) -> None:
    """404 si el edificio no existe o no alcanza; 403 sin `revertir_o_reimputar_pago` en él."""
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise HTTPException(status_code=404, detail="no encontrado")
    if not puede(asignaciones, Accion.REVERTIR_O_REIMPUTAR_PAGO, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": Accion.REVERTIR_O_REIMPUTAR_PAGO.value,
            },
        )


@router.post("/complejos/{complejo_id}/pagos/lectura", status_code=201)
def subir_comprobante(
    complejo_id: UUID,
    archivo: Annotated[UploadFile, File()],
    fecha_de_hoy: date = Depends(hoy),
    el_lector: LectorDeComprobantes | None = Depends(lector),
    tope: float = Depends(tope_de_lectura),
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Guarda el comprobante (JPEG, PNG o PDF de hasta 10 MB, por sus primeros bytes) y lo lee
    con IA si hay lector (H-019); la lectura fallida no es un error. Se lee un byte de más del
    tope para saber que se pasó sin cargar un archivo enorme en memoria."""
    _edificio_autorizado(sesion, identidad, complejo_id)
    contenido = archivo.file.read(TAMANO_MAXIMO + 1)
    guardado = comprobantes.guardar_comprobante(
        sesion,
        identidad,
        complejo_id=complejo_id,
        contenido=contenido,
        lector=el_lector,
        tope=tope,
        hoy=fecha_de_hoy,
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


@router.post("/complejos/{complejo_id}/pagos/{pago_id}/confirmacion")
def confirmar_un_pago(
    complejo_id: UUID,
    pago_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_de_quien_confirma(sesion, identidad, complejo_id)
    confirmacion = resolver.confirmar_pago(
        sesion,
        identidad,
        complejo_id=complejo_id,
        pago_id=pago_id,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    respuesta = {"pago_id": str(pago_id), "estado": confirmacion.estado}
    if confirmacion.ajuste_sin_destino is not None:
        respuesta["ajuste_sin_destino"] = confirmacion.ajuste_sin_destino.a_texto()
    return respuesta


@router.post("/complejos/{complejo_id}/pagos/{pago_id}/rechazo")
def rechazar_un_pago(
    complejo_id: UUID,
    pago_id: UUID,
    cuerpo: Annotated[Any, Body()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_de_quien_confirma(sesion, identidad, complejo_id)
    estado = resolver.rechazar_pago(
        sesion,
        identidad,
        complejo_id=complejo_id,
        pago_id=pago_id,
        cuerpo=cuerpo,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"pago_id": str(pago_id), "estado": estado}


@router.post("/complejos/{complejo_id}/pagos/{pago_id}/reversion")
def revertir_un_pago(
    complejo_id: UUID,
    pago_id: UUID,
    cuerpo: Annotated[Any, Body()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_de_quien_revierte(sesion, identidad, complejo_id)
    estado = resolver.revertir_pago_confirmado(
        sesion,
        identidad,
        complejo_id=complejo_id,
        pago_id=pago_id,
        cuerpo=cuerpo,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"pago_id": str(pago_id), "estado": estado}


@router.post("/complejos/{complejo_id}/pagos/{pago_id}/reimputacion")
def reimputar_un_pago(
    complejo_id: UUID,
    pago_id: UUID,
    cuerpo: Annotated[Any, Body()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    _edificio_de_quien_revierte(sesion, identidad, complejo_id)
    estado = resolver.reimputar_pago_confirmado(
        sesion,
        identidad,
        complejo_id=complejo_id,
        pago_id=pago_id,
        cuerpo=cuerpo,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {"pago_id": str(pago_id), "estado": estado}


@router.post("/complejos/{complejo_id}/pagos/{pago_id}/comprobante/enlace", status_code=201)
def enlace_del_comprobante(
    complejo_id: UUID,
    pago_id: UUID,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    """Un enlace firmado que vence a los 15 minutos. Lo pide quien puede ver el pago (la regla de
    `GET .../pagos/{id}`: 404 si no, 403 sin permiso en el edificio)."""
    asignaciones = _edificio_autorizado(sesion, identidad, complejo_id)
    pago = lectura.leer_pago(
        sesion,
        complejo_id=complejo_id,
        pago_id=pago_id,
        unidades=unidades_del_alcance(asignaciones, complejo_id),
    )
    if pago is None:
        raise NoEncontrado
    try:
        clave = request.app.state.configuracion.clave_de_enlaces()
    except ConfiguracionInvalida:
        raise HTTPException(status_code=503, detail="enlaces_no_configurados") from None
    vence_en = (datetime.now(UTC) + VIGENCIA_DEL_ENLACE).replace(microsecond=0)
    token = enlaces.firmar_enlace_del_comprobante(
        administracion_id=identidad.administracion_id,
        pago_id=pago_id,
        vence_en=vence_en,
        clave=clave,
    )
    return {"url": f"/api/comprobantes/descarga?token={token}", "vence_en": vence_en.isoformat()}


@router_de_descarga.get("/comprobantes/descarga")
def descargar_el_comprobante(request: Request, token: Annotated[str, Query()]) -> Response:
    """Sin sesión: el token firmado es la autorización. 200 con los bytes subidos y su tipo; 410
    vencido; 403 alterado, de otro tipo, de otro pago o de otra administración. Nunca se abre una
    sesión de base antes de verificar la firma, y el tenant sale del token verificado."""
    try:
        clave = request.app.state.configuracion.clave_de_enlaces()
    except ConfiguracionInvalida:
        raise HTTPException(status_code=503, detail="enlaces_no_configurados") from None
    try:
        enlace = enlaces.verificar_enlace_del_comprobante(
            token, clave=clave, ahora=datetime.now(UTC)
        )
    except EnlaceVencido:
        raise HTTPException(status_code=410, detail="enlace_vencido") from None
    except enlaces.EnlaceAlterado:
        raise HTTPException(status_code=403, detail="enlace_invalido") from None
    sesion = abrir_sesion(request.app.state.fabrica_de_sesiones, enlace.administracion_id)
    try:
        archivado = lectura.comprobante_del_pago(sesion, pago_id=enlace.pago_id)
        sesion.rollback()
    finally:
        sesion.close()
    if archivado is None:
        raise HTTPException(status_code=403, detail="enlace_invalido")
    contenido, tipo = archivado
    return Response(
        content=contenido,
        media_type=comprobantes.TIPOS_MIME[tipo],
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
