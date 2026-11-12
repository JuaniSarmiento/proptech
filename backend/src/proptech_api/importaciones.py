"""Importación del padrón desde Excel (change 5, H-007): subir la plantilla y descargarla.

El caso de uso `importar` autoriza solo (404 sin alcance, 403 sin permiso, D7) y abre su
transacción; la ruta sólo lee el archivo con su tope de bytes, parsea la fecha, mapea las
excepciones a HTTP y confirma.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_api.complejos import _edificio_autorizado
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.importacion.adaptadores.excel import LectorDePlantillaExcel, plantilla_vacia
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
