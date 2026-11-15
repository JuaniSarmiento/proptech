"""Liquidación y emisión de las expensas (change 7, D-157): la preliquidación sin efectos (H-011).

Mismo orden de D7 que `gastos.py`: cargar el edificio → 404 si no existe o no alcanza → 403 si no
puede → el pedido mismo (422) → el estado del edificio (409). La lectura pide la acción
`cargar_gastos_y_preparar_liquidacion`; no se agrega ninguna a la matriz de D-106.
"""

import re
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.liquidacion.aplicacion import preliquidacion
from proptech_core.liquidacion.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)

_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)


async def manejar_error_de_liquidacion(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, NoEncontrado):
        return JSONResponse(status_code=404, content={"detail": "no encontrado"})
    if isinstance(error, Conflicto):
        return JSONResponse(
            status_code=409,
            content={"detail": "conflicto", "campo": error.campo, "motivo": error.motivo},
        )
    if isinstance(error, EntradaInvalida):
        item = {"loc": ["path", error.campo], "msg": error.motivo, "type": "value_error"}
        return JSONResponse(status_code=422, content={"detail": [item]})
    raise TypeError("error de liquidación inesperado")


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> None:
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise HTTPException(status_code=404, detail="no encontrado")
    if not puede(asignaciones, accion, complejo_id):
        raise HTTPException(
            status_code=403,
            detail={
                "codigo": "sin_permiso",
                "detalle": "sin_permiso",
                "permiso_faltante": accion.value,
            },
        )


def _periodo(texto: str) -> date:
    """`AAAA-MM-01`: una fecha ISO con día 1. Se lee a mano (no como `date` del path) para que el
    422 llegue después del 404 y del 403, en el orden de D7."""
    try:
        if not _FECHA.fullmatch(texto):
            raise ValueError
        periodo = date.fromisoformat(texto)
    except ValueError:
        raise EntradaInvalida("periodo", "fecha inválida") from None
    if periodo.day != 1:
        raise EntradaInvalida("periodo", "el período es el día 1 del mes")
    return periodo


@router.get("/complejos/{complejo_id}/periodos/{periodo}/preliquidacion")
def preliquidacion_del_periodo(
    complejo_id: UUID,
    periodo: str,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    _edificio_autorizado(
        sesion, identidad, complejo_id, Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION
    )
    return preliquidacion.preliquidar_periodo(
        sesion, complejo_id=complejo_id, periodo=_periodo(periodo)
    )
