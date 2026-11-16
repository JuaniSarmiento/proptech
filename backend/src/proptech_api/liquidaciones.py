"""Liquidación y emisión de las expensas (change 7, D-157): la preliquidación sin efectos (H-011).

Mismo orden de D7 que `gastos.py`: cargar el edificio → 404 si no existe o no alcanza → 403 si no
puede → el pedido mismo (422) → el estado del edificio (409). La preliquidación pide la acción
`cargar_gastos_y_preparar_liquidacion`; emitir, `emitir_y_distribuir_liquidacion` (y, si acepta un
bloqueante, `aceptar_alertas_bloqueantes`); leer lo emitido, `ver_liquidaciones` (H-013).
"""

import re
from datetime import UTC, date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from proptech_api.acceso import RutaConIdentidad, identidad_actual, sesion_con_tenant
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.liquidacion.aplicacion import cargos, ciclo, emision, preliquidacion
from proptech_core.liquidacion.aplicacion.errores import (
    Conflicto,
    ControlDuro,
    EntradaInvalida,
    NoEncontrado,
    SinPermiso,
)
from proptech_core.liquidacion.aplicacion.lectura import (
    leer_liquidacion,
    listar_liquidaciones,
    ve_lo_no_distribuido,
)
from proptech_core.liquidacion.dominio.ciclo import (
    PedidoInvalido,
    pedido_de_cargo,
    visible_para_el_consejo,
)

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
        item = {"loc": [error.donde, error.campo], "msg": error.motivo, "type": "value_error"}
        return JSONResponse(status_code=422, content={"detail": [item]})
    if isinstance(error, ControlDuro):
        return JSONResponse(
            status_code=422,
            content={"detail": "control_duro", "controles": list(error.codigos)},
        )
    if isinstance(error, SinPermiso):
        return JSONResponse(status_code=403, content={"detail": _sin_permiso(error.accion)})
    raise TypeError("error de liquidación inesperado")


def _sin_permiso(accion: str) -> dict[str, str]:
    return {"codigo": "sin_permiso", "detalle": "sin_permiso", "permiso_faltante": accion}


def _edificio_autorizado(
    sesion: Session, identidad: Identidad, complejo_id: UUID, accion: Accion
) -> None:
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if edificio is None or not alcanza(asignaciones, complejo_id):
        raise HTTPException(status_code=404, detail="no encontrado")
    if not puede(asignaciones, accion, complejo_id):
        raise HTTPException(status_code=403, detail=_sin_permiso(accion.value))


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


@router.post("/complejos/{complejo_id}/periodos/{periodo}/emision")
def emitir_la_liquidacion(
    complejo_id: UUID,
    periodo: str,
    response: Response,
    cuerpo: Annotated[dict[str, Any], Body()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Emite exactamente la preliquidación revisada (la huella). El cuerpo se valida a mano, después
    del 404 y del 403 (D7), no por FastAPI. 201 emitida; 200 si es el mismo pedido otra vez."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION)
    hecha = emision.emitir_liquidacion(
        sesion,
        identidad,
        complejo_id=complejo_id,
        periodo=_periodo(periodo),
        cuerpo=cuerpo,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    response.status_code = 201 if hecha.nueva else 200
    return hecha.respuesta


@router.get("/complejos/{complejo_id}/liquidaciones")
def liquidaciones_del_edificio(
    complejo_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> list[dict[str, Any]]:
    """De la más nueva a la más vieja. El consejo no ve lo emitido sin distribuir (P39, D-157)."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_LIQUIDACIONES)
    completa = ve_lo_no_distribuido(cargar_asignaciones(sesion, identidad.persona_id), complejo_id)
    return listar_liquidaciones(sesion, complejo_id=complejo_id, solo_distribuidas=not completa)


@router.get("/complejos/{complejo_id}/liquidaciones/{liquidacion_id}")
def liquidacion_emitida(
    complejo_id: UUID,
    liquidacion_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, Any]:
    """Lo guardado al emitir, nunca recalculado (E2), con su estado. Al consejo, una liquidación
    emitida sin distribuir le da 404 (P39, D-157)."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.VER_LIQUIDACIONES)
    emitida = leer_liquidacion(sesion, complejo_id=complejo_id, liquidacion_id=liquidacion_id)
    if emitida is None:
        raise NoEncontrado
    completa = ve_lo_no_distribuido(cargar_asignaciones(sesion, identidad.persona_id), complejo_id)
    if not completa and not visible_para_el_consejo(emitida["estado"]):
        raise NoEncontrado
    return emitida


@router.post("/complejos/{complejo_id}/liquidaciones/{liquidacion_id}/distribucion")
def distribuir_la_liquidacion(
    complejo_id: UUID,
    liquidacion_id: UUID,
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    """La distribución manual (E9): 409 si ya estaba distribuida o está anulada."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION)
    hecha = ciclo.distribuir_liquidacion(
        sesion,
        identidad,
        complejo_id=complejo_id,
        liquidacion_id=liquidacion_id,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return hecha


@router.post("/complejos/{complejo_id}/liquidaciones/{liquidacion_id}/anulacion")
def anular_la_liquidacion(
    complejo_id: UUID,
    liquidacion_id: UUID,
    cuerpo: Annotated[dict[str, Any], Body()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    """Anula con motivo (E10): 409 si está distribuida, ya anulada o con el período siguiente
    emitido (P26). El cuerpo se valida a mano, después del 404 y del 403 (D7)."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.ANULAR_LIQUIDACION)
    hecha = ciclo.anular_liquidacion(
        sesion,
        identidad,
        complejo_id=complejo_id,
        liquidacion_id=liquidacion_id,
        cuerpo=cuerpo,
        request_id=UUID(request_id_actual.get() or ""),
    )
    sesion.commit()
    return hecha


@router.post(
    "/complejos/{complejo_id}/unidades/{unidad_id}/cargos-cobrados-de-menos", status_code=201
)
def registrar_un_cargo_cobrado_de_menos(
    complejo_id: UUID,
    unidad_id: UUID,
    cuerpo: Annotated[dict[str, Any], Body()],
    identidad: Identidad = Depends(identidad_actual),
    sesion: Session = Depends(sesion_con_tenant),
) -> dict[str, str]:
    """Corrige con una obligación nueva un cargo cobrado de menos (E11). El replay por
    `operacion_id` da el mismo cuerpo con 201 y no escribe nada."""
    _edificio_autorizado(sesion, identidad, complejo_id, Accion.CORREGIR_MOVIMIENTO)
    try:
        pedido = pedido_de_cargo(cuerpo)
    except PedidoInvalido as error:
        raise EntradaInvalida(error.campo, donde="body") from None
    cargo = cargos.registrar_cargo_cobrado_de_menos(
        sesion,
        identidad,
        complejo_id=complejo_id,
        unidad_id=unidad_id,
        obligacion_origen_id=pedido.obligacion_origen_id,
        operacion_id=pedido.operacion_id,
        importe=pedido.importe,
        componente=pedido.componente,
        motivo=pedido.motivo,
        request_id=UUID(request_id_actual.get() or ""),
        reloj=lambda: datetime.now(UTC),
    )
    sesion.commit()
    return {
        "cargo_id": str(cargo.cargo_id),
        "obligacion_id": str(cargo.obligacion_id),
        "obligacion_origen_id": str(cargo.obligacion_origen_id),
        "importe": cargo.importe.a_texto(),
        "componente": cargo.componente,
        "vencimiento": cargo.vencimiento.isoformat(),
        "motivo": cargo.motivo,
        "registrado_por": str(cargo.registrado_por),
        "registrado_en": cargo.registrado_en.isoformat(),
    }
