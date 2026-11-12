"""Importación del padrón y de los saldos desde Excel (change 5): subir la plantilla y descargarla
(H-007), leer la comparación del borrador y aceptar sus diferencias (H-008) y confirmar los saldos
(H-009) y ajustar el saldo inicial de una unidad ya confirmada (H-010).

Cada caso de uso (`importar`, `comparar_borrador`, `aceptar_diferencias`, `confirmar`) autoriza
solo (404 sin alcance, 403 sin permiso, D7) y abre su transacción; la ruta sólo lee el archivo con
su tope de bytes y parsea la fecha (subir), mapea las excepciones a HTTP y confirma. `NoEncontrado`
y `Conflicto` los traduce el manejador de `complejos` (404 y 409 con su `campo`); los del libro (el
422 de `fecha_de_migracion` y los 409 de la carga), el del libro; el 422 del cuerpo del ajuste
es de Pydantic.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import AfterValidator, Field, field_validator
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.complejos import _edificio_autorizado
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.importacion.adaptadores.excel import LectorDePlantillaExcel, plantilla_vacia
from proptech_core.importacion.aplicacion.aceptar import aceptar_diferencias
from proptech_core.importacion.aplicacion.ajuste import AjusteRegistrado, ajustar_saldo_inicial
from proptech_core.importacion.aplicacion.borrador import AceptacionRegistrada
from proptech_core.importacion.aplicacion.comparar import comparar_borrador
from proptech_core.importacion.aplicacion.confirmar import confirmar
from proptech_core.importacion.aplicacion.errores import ArchivoYaImportado, SinPermiso
from proptech_core.importacion.aplicacion.importar import importar
from proptech_core.importacion.dominio.padron import PadronInvalido
from proptech_core.importacion.dominio.plantilla import (
    LIMITE_DE_BYTES,
    ArchivoInvalido,
    ErrorDeImportacion,
)

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _como_json(error: ErrorDeImportacion) -> dict[str, object]:
    return {
        "hoja": error.hoja,
        "fila": error.fila,
        "columna": error.columna,
        "motivo": error.motivo,
    }


async def manejar_error_de_importacion(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, SinPermiso):
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
    if isinstance(error, ArchivoYaImportado):
        return JSONResponse(
            status_code=409,
            content={
                "detail": "conflicto",
                "campo": error.campo,
                "importacion_id": str(error.importacion_id),
            },
        )
    if isinstance(error, ArchivoInvalido | PadronInvalido):
        return JSONResponse(
            status_code=422, content={"detail": [_como_json(e) for e in error.errores]}
        )
    raise TypeError("error de importación inesperado")


def _fecha(texto: str | None) -> date | None:
    """ISO `AAAA-MM-DD` estricta; cualquier otra cosa es `None` (el caso de uso la rechaza)."""
    if texto is None or len(texto) != 10:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


@router.post("/complejos/{complejo_id}/importaciones", status_code=201)
async def importar_padron(
    complejo_id: UUID,
    archivo: UploadFile = File(...),
    fecha_de_migracion: str | None = Form(None),
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, object]:
    # D1: nunca más de un byte por encima del tope; el lector lo rechaza con su mensaje.
    contenido = await archivo.read(LIMITE_DE_BYTES + 1)
    resultado = importar(
        sesion,
        identidad,
        complejo_id=complejo_id,
        contenido=contenido,
        nombre_del_archivo=archivo.filename,
        fecha_de_migracion=_fecha(fecha_de_migracion),
        lector=LectorDePlantillaExcel(),
        reloj=lambda: datetime.now(UTC),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {
        "importacion_id": str(resultado.importacion_id),
        "unidades_creadas": resultado.unidades_creadas,
        "propietarios_creados": resultado.propietarios_creados,
        "propietarios_reusados": resultado.propietarios_reusados,
        "filas_de_saldo": resultado.filas_de_saldo,
        "advertencias": [_como_json(a) for a in resultado.advertencias],
    }


@router.get("/complejos/{complejo_id}/importaciones/plantilla")
def descargar_plantilla(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> Response:
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.IMPORTAR_PADRON_Y_SALDOS)
    return Response(
        content=plantilla_vacia(),
        media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="plantilla-padron.xlsx"'},
    )


def _aceptacion_como_json(aceptacion: AceptacionRegistrada) -> dict[str, object]:
    return {
        "aceptacion_id": str(aceptacion.aceptacion_id),
        "diferencias": [
            {
                "unidad": d.unidad,
                "borrador": d.borrador,
                "control": d.control,
                "diferencia": d.diferencia,
            }
            for d in aceptacion.diferencias
        ],
        "aceptada_por": str(aceptacion.aceptada_por),
        "aceptada_en": aceptacion.aceptada_en.isoformat(),
    }


@router.get("/complejos/{complejo_id}/importaciones/comparacion")
def leer_comparacion(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, object]:
    """El borrador vigente del edificio contra el control, unidad por unidad (D6, E13)."""
    comparacion = comparar_borrador(sesion, identidad, complejo_id=complejo_id)
    return {
        "importacion_id": str(comparacion.importacion_id),
        "unidades": [
            {
                "unidad": u.unidad,
                "unidad_id": str(u.unidad_id),
                "borrador": u.borrador.a_texto(),
                "control": u.control.a_texto(),
                "diferencia": u.diferencia.a_texto(),
                "aviso": u.aviso,
            }
            for u in comparacion.unidades
        ],
        "total_borrador": comparacion.total_borrador.a_texto(),
        "total_control": comparacion.total_control.a_texto(),
        "unidades_con_diferencia": comparacion.unidades_con_diferencia,
        "requiere_aceptacion": comparacion.requiere_aceptacion,
        "aceptacion": (
            None
            if comparacion.aceptacion is None
            else _aceptacion_como_json(comparacion.aceptacion)
        ),
    }


class CuerpoAceptacion(CuerpoDeAlta):
    #: Una referencia al borrador que se mira, no un alta: el id lo elige el servidor al aceptar.
    importacion_id: Annotated[UUID, Field(strict=False)]


@router.post("/complejos/{complejo_id}/importaciones/aceptacion-de-diferencias", status_code=201)
def aceptar_las_diferencias(
    complejo_id: UUID,
    cuerpo: CuerpoAceptacion,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, object]:
    """Acepta las diferencias del borrador vigente (E6, E8); 404, 403 y 409 son del caso de uso."""
    aceptacion = aceptar_diferencias(
        sesion,
        identidad,
        complejo_id=complejo_id,
        importacion_id=cuerpo.importacion_id,
        reloj=lambda: datetime.now(UTC),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return _aceptacion_como_json(aceptacion)


@router.post("/complejos/{complejo_id}/importaciones/confirmacion", status_code=201)
def confirmar_los_saldos(
    complejo_id: UUID,
    cuerpo: CuerpoAceptacion,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, object]:
    """Confirma el borrador vigente: carga el saldo inicial en el libro, pasa el edificio a
    `confirmada` y cierra el importador (E6, E8, E10, E15). 404, 403, 409 y el 422 de la fecha de
    migración son del caso de uso. El cuerpo es la misma referencia al borrador que el de aceptar.
    """
    confirmada = confirmar(
        sesion,
        identidad,
        complejo_id=complejo_id,
        importacion_id=cuerpo.importacion_id,
        reloj=lambda: datetime.now(UTC),
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return {
        "importacion_id": str(confirmada.importacion_id),
        "carga_id": str(confirmada.carga_id),
        "estado_migracion": confirmada.estado_migracion,
        "totales": {
            "capital": confirmada.totales.capital.a_texto(),
            "interes_importado": confirmada.totales.interes_importado.a_texto(),
            "credito": confirmada.totales.credito.a_texto(),
        },
        "confirmada_por": str(confirmada.confirmada_por),
        "confirmada_en": confirmada.confirmada_en.isoformat(),
    }


def _importe_positivo(importe: Dinero) -> Dinero:
    if importe <= Dinero("0.00"):
        raise ValueError("el importe debe ser positivo")
    return importe


class CuerpoAjuste(CuerpoDeAlta):
    operacion_id: Annotated[UUID, Field(strict=False)]
    importe: Annotated[Dinero, AfterValidator(_importe_positivo)]
    #: `interes` no se ajusta: el interés lo calcula la emisión (R03).
    componente: Literal["ordinaria", "fondo_de_reserva", "extraordinaria"]
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_valido(cls, motivo: str) -> str:
        motivo = recortado_sin_control(motivo)
        if not 1 <= len(motivo) <= 500:
            raise ValueError("el motivo debe tener de 1 a 500 caracteres")
        return motivo


def _ajuste_como_json(ajuste: AjusteRegistrado) -> dict[str, object]:
    return {
        "ajuste_id": str(ajuste.ajuste_id),
        "operacion_id": str(ajuste.operacion_id),
        "obligacion_id": str(ajuste.obligacion_id),
        "cuenta_id": str(ajuste.cuenta_id),
        "unidad_id": str(ajuste.unidad_id),
        "importe": ajuste.importe.a_texto(),
        "componente": ajuste.componente,
        "periodo": ajuste.periodo.isoformat(),
        "vencimiento": ajuste.vencimiento.isoformat(),
        "motivo": ajuste.motivo,
        "registrado_por": str(ajuste.registrado_por),
        "registrado_en": ajuste.registrado_en.isoformat(),
    }


@router.post(
    "/complejos/{complejo_id}/unidades/{unidad_id}/ajustes-de-saldo-inicial", status_code=201
)
def ajustar_el_saldo_inicial(
    complejo_id: UUID,
    unidad_id: UUID,
    cuerpo: CuerpoAjuste,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, object]:
    """Corrige con una obligación nueva un saldo cargado de menos (E6, E11). 404, 403, 409
    (`estado_migracion`, `operacion_id`) y el 422 del libro son del caso de uso; el replay da el
    mismo cuerpo con 201 y no escribe nada.
    """
    ajuste = ajustar_saldo_inicial(
        sesion,
        identidad,
        complejo_id=complejo_id,
        unidad_id=unidad_id,
        operacion_id=cuerpo.operacion_id,
        importe=cuerpo.importe,
        componente=cuerpo.componente,
        motivo=cuerpo.motivo,
        request_id=UUID(request_id_actual.get() or ""),
        reloj=lambda: datetime.now(UTC),
    )
    sesion.commit()
    return _ajuste_como_json(ajuste)
