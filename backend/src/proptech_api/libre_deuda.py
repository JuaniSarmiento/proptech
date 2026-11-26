"""El certificado de libre deuda de una unidad (10b, H-041, R21, D-171, D-172): emitirlo, listar los
de ella y bajar el PDF de cada uno.

Los dos casos de uso autorizan solos, en el orden de D7: el edificio que no existe o no alcanza, o
la unidad que no es de él, da 404; sin `emitir_libre_deuda` (que también cubre listar), 403; la
entrada que no sirve, 422. `NoEncontrado` y `EntradaInvalida` los traduce el manejador de
`complejos`. La descarga es pública por diseño: el token firmado ES la autorización (D-070).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.configuracion import ConfiguracionInvalida
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
from proptech_core.libre_deuda.aplicacion import enlaces
from proptech_core.libre_deuda.aplicacion.certificado import Certificado
from proptech_core.libre_deuda.aplicacion.emitir import emitir_libre_deuda
from proptech_core.libre_deuda.aplicacion.errores import SinPermiso
from proptech_core.libre_deuda.aplicacion.lectura import listar_certificados, pdf_del_certificado

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)
#: La descarga del PDF: pública por diseño. El token firmado ES la autorización (D-070), así que no
#: pasa por la identidad; el tenant sale del token ya verificado, nunca del pedido.
router_de_descarga = APIRouter(prefix="/api")

#: Cuánto dura un enlace de descarga (D-070), el mismo del 7.
VIGENCIA_DEL_ENLACE = timedelta(minutes=15)


def hoy() -> date:
    """La fecha de hoy en Mendoza. Es una dependencia para que la aceptación la fije (L-090)."""
    return hoy_en_mendoza(lambda: datetime.now(UTC))


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


class CuerpoLibreDeuda(CuerpoDeAlta):
    #: Sin tipo: el caso de uso la lee, para que su 422 llegue después del 404 y del 403 (D7).
    fecha_de_corte: Any = None


def _clave_de_enlaces(request: Request) -> str:
    try:
        return str(request.app.state.configuracion.clave_de_enlaces())
    except ConfiguracionInvalida:
        raise HTTPException(status_code=503, detail="enlaces_no_configurados") from None


def _como_json(request: Request, identidad: Identidad, c: Certificado) -> dict[str, Any]:
    vence_en = (datetime.now(UTC) + VIGENCIA_DEL_ENLACE).replace(microsecond=0)
    token = enlaces.firmar_enlace(
        administracion_id=identidad.administracion_id,
        certificado_id=c.id,
        vence_en=vence_en,
        clave=_clave_de_enlaces(request),
    )
    return {
        "id": str(c.id),
        "unidad_id": str(c.unidad_id),
        "fecha_de_corte": c.fecha_de_corte.isoformat(),
        "emitido_en": c.emitido_en.isoformat(),
        "saldo": c.saldo,
        "capital": c.capital,
        "interes_corrido": c.interes_corrido,
        "intereses": c.intereses,
        "libre_de_deuda": c.libre_de_deuda,
        "en_revision": [dict(p) for p in c.en_revision],
        "vencen_despues": [dict(q) for q in c.vencen_despues],
        "huella": c.huella,
        "en_gestion_judicial": c.en_gestion_judicial,
        "enlace": {
            "url": f"/api/libre-deuda/descarga?token={token}",
            "vence_en": vence_en.isoformat(),
        },
    }


@router.post("/complejos/{complejo_id}/unidades/{unidad_id}/libre-deuda", status_code=201)
def emitir(
    request: Request,
    complejo_id: UUID,
    unidad_id: UUID,
    cuerpo: CuerpoLibreDeuda,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
    fecha_de_hoy: date = Depends(hoy),
) -> dict[str, Any]:
    """Emite el certificado a la fecha de corte (no posterior a hoy), lo guarda con su PDF y lo
    audita. Cada pedido crea un certificado nuevo. No escribe en el libro."""
    certificado = emitir_libre_deuda(
        sesion,
        identidad,
        complejo_id=complejo_id,
        unidad_id=unidad_id,
        fecha_de_corte=cuerpo.fecha_de_corte,
        hoy=fecha_de_hoy,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return _como_json(request, identidad, certificado)


@router.get("/complejos/{complejo_id}/unidades/{unidad_id}/libre-deuda")
def listar(
    request: Request,
    complejo_id: UUID,
    unidad_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    certificados = listar_certificados(
        sesion, identidad, complejo_id=complejo_id, unidad_id=unidad_id
    )
    return [_como_json(request, identidad, c) for c in certificados]


@router_de_descarga.get("/libre-deuda/descarga")
def descargar(request: Request, token: Annotated[str, Query()]) -> Response:
    """Sin sesión: el token firmado es la autorización. 200 con el PDF guardado al emitir; 410
    vencido; 403 alterado, de otro tipo o con la firma mal; 404 si la firma es buena y el
    certificado no existe. Nunca se abre una sesión de base antes de verificar la firma, y el tenant
    sale del token verificado."""
    try:
        enlace = enlaces.verificar_enlace(
            token, clave=_clave_de_enlaces(request), ahora=datetime.now(UTC)
        )
    except enlaces.EnlaceVencido:
        raise HTTPException(status_code=410, detail="enlace_vencido") from None
    except enlaces.EnlaceAlterado:
        raise HTTPException(status_code=403, detail="enlace_invalido") from None
    sesion = abrir_sesion(request.app.state.fabrica_de_sesiones, enlace.administracion_id)
    try:
        archivado = pdf_del_certificado(sesion, certificado_id=enlace.certificado_id)
        sesion.rollback()
    finally:
        sesion.close()
    if archivado is None:
        raise HTTPException(status_code=404, detail="no encontrado")
    contenido, nombre = archivado
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
