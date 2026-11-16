"""Distribuir y anular una liquidación emitida (E9, E10, P26, D-157).

Orden de chequeo (el router ya cargó el edificio, 404, y pidió el permiso, 403): el cuerpo (422) ->
el candado del período, `FOR UPDATE` sobre la fila de `complejo` **antes** que los candados de
cuentas (E5) -> la liquidación del edificio (404) -> su estado (409) -> recién ahí las escrituras.
Un rechazo no escribe nada. Anular y distribuir toman el mismo candado: si llegan juntas, gana una y
la otra encuentra el estado ya cambiado (409): nunca los dos eventos. No commitea: lo hace el
llamador.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.complejos.aplicacion.errores import transaccion
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion.creditos import ahora_utc
from proptech_core.cuenta_corriente.aplicacion.emisiones import anular_emision
from proptech_core.cuenta_corriente.aplicacion.liquidar import hay_emision_posterior
from proptech_core.liquidacion.aplicacion.distribucion import registrar_distribucion
from proptech_core.liquidacion.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.liquidacion.aplicacion.lectura import (
    emision_de_la_liquidacion,
    estado_de_la_emision,
)
from proptech_core.liquidacion.dominio.ciclo import (
    ANULADA,
    DISTRIBUIDA,
    PedidoInvalido,
    conflicto_al_anular,
    conflicto_al_distribuir,
    pedido_de_anulacion,
)


def distribuir_liquidacion(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    liquidacion_id: UUID,
    request_id: UUID,
    reloj: Callable[[], datetime] = ahora_utc,
) -> dict[str, str]:
    """La distribución manual (origen `manual`): audita `emitir_y_distribuir_liquidacion`."""
    with transaccion(sesion, {}):
        if cargar_complejo(sesion, complejo_id, bloquear=True) is None:
            raise NoEncontrado
        ubicada = emision_de_la_liquidacion(
            sesion, complejo_id=complejo_id, liquidacion_id=liquidacion_id
        )
        if ubicada is None:
            raise NoEncontrado
        emision_id, periodo = ubicada
        choque = conflicto_al_distribuir(estado_de_la_emision(sesion, emision_id))
        if choque is not None:
            raise Conflicto(*choque)
        if registrar_distribucion(
            sesion,
            emision_id=emision_id,
            origen="manual",
            persona_id=identidad.persona_id,
            request_id=request_id,
            reloj=reloj,
        ):
            registrar(
                sesion,
                identidad,
                Accion.EMITIR_Y_DISTRIBUIR_LIQUIDACION,
                entidad="liquidacion",
                entidad_id=liquidacion_id,
                request_id=request_id,
                detalle={
                    "complejo_id": str(complejo_id),
                    "periodo": periodo.isoformat(),
                    "emision_id": str(emision_id),
                    "origen": "manual",
                },
            )
    return {"estado": DISTRIBUIDA}


def anular_liquidacion(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    liquidacion_id: UUID,
    cuerpo: Mapping[str, Any],
    request_id: UUID,
    reloj: Callable[[], datetime] = ahora_utc,
) -> dict[str, str]:
    """Anula con motivo: agrega el evento `anulada` por el libro (`anular_emision`, que toma los
    candados de las cuentas alcanzadas) y audita `anular_liquidacion` en la misma transacción. No
    toca ningún movimiento, obligación ni imputación (R08): el efecto se calcula."""
    try:
        motivo = pedido_de_anulacion(cuerpo)
    except PedidoInvalido as error:
        raise EntradaInvalida(error.campo, donde="body") from None
    with transaccion(sesion, {}):
        if cargar_complejo(sesion, complejo_id, bloquear=True) is None:
            raise NoEncontrado
        ubicada = emision_de_la_liquidacion(
            sesion, complejo_id=complejo_id, liquidacion_id=liquidacion_id
        )
        if ubicada is None:
            raise NoEncontrado
        emision_id, periodo = ubicada
        choque = conflicto_al_anular(
            estado_de_la_emision(sesion, emision_id),
            siguiente_emitido=hay_emision_posterior(
                sesion, complejo_id=complejo_id, periodo=periodo
            ),
        )
        if choque is not None:
            raise Conflicto(*choque)
        anular_emision(
            sesion,
            identidad,
            emision_id=emision_id,
            motivo=motivo,
            request_id=request_id,
            reloj=reloj,
        )
        registrar(
            sesion,
            identidad,
            Accion.ANULAR_LIQUIDACION,
            entidad="liquidacion",
            entidad_id=liquidacion_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "periodo": periodo.isoformat(),
                "emision_id": str(emision_id),
            },
        )
    return {"estado": ANULADA}
