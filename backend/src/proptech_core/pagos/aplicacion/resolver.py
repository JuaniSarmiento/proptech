"""Resolver un pago informado (E6, E13, D-166): confirmarlo lo imputa en el libro, rechazarlo no.

Orden de lo que decide la base: el pago (404), el motivo del rechazo (422) y el estado (409).
Confirmar y rechazar toman primero un candado de transacción por pago: dos resoluciones del mismo
pago se serializan y la segunda lee el evento de la primera. Confirmar un pago ya confirmado es una
repetición (devuelve lo mismo sin escribir); confirmar o rechazar uno rechazado o revertido, o
rechazar uno confirmado, es un conflicto de estado. Después se bloquean, en orden, las cuentas de
todas las partes (D2) antes de escribir nada, y todo va en la transacción del llamador: si falla un
paso no queda ninguno.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.eventos import EventoDelPago
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.cuenta_corriente.aplicacion import pagos as libro_de_pagos
from proptech_core.cuenta_corriente.aplicacion.cuentas import (
    bloquear_cuentas,
    crear_cuentas_de_unidades,
)
from proptech_core.pagos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.pagos.dominio.estado import INFORMADO, estado_del_pago

#: Fijo: de él sale el `operacion_id` de cada parte (confirmar dos veces es una repetición).
_ESPACIO_DE_OPERACIONES = UUID("5d1c3a9e-0b7f-4c52-9a4e-8e2f6b1d7c30")

CONFIRMADO = "confirmado"
RECHAZADO = "rechazado"


@dataclass(frozen=True)
class ParteDelPago:
    id: UUID
    unidad_id: UUID
    importe: Dinero


@dataclass(frozen=True)
class PagoParaResolver:
    id: UUID
    complejo_id: UUID
    fecha_de_transferencia: date
    cbu_origen: str | None
    partes: tuple[ParteDelPago, ...]


def _cargar(sesion: Session, complejo_id: UUID, pago_id: UUID) -> PagoParaResolver:
    """404 si no existe, es de otro edificio o de otra administración (la RLS lo esconde)."""
    fila = sesion.execute(
        text(
            "SELECT id, fecha_de_transferencia, cbu_origen FROM pago_informado "
            "WHERE id = :pago AND complejo_id = :c"
        ),
        {"pago": pago_id, "c": complejo_id},
    ).one_or_none()
    if fila is None:
        raise NoEncontrado
    partes = sesion.execute(
        text(
            "SELECT id, unidad_id, importe::text AS importe FROM parte_de_pago "
            "WHERE pago_id = :pago ORDER BY unidad_id"
        ),
        {"pago": pago_id},
    ).all()
    return PagoParaResolver(
        UUID(str(fila.id)),
        complejo_id,
        fila.fecha_de_transferencia,
        fila.cbu_origen,
        tuple(
            ParteDelPago(UUID(str(p.id)), UUID(str(p.unidad_id)), Dinero(p.importe)) for p in partes
        ),
    )


def _tomar_el_pago(sesion: Session, identidad: Identidad, pago_id: UUID) -> None:
    sesion.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:clave, 0))"),
        {"clave": f"resolver_pago|{identidad.administracion_id}|{pago_id}"},
    )


def _estado(sesion: Session, pago_id: UUID) -> str:
    tipos = sesion.execute(
        text("SELECT tipo FROM evento_de_pago WHERE pago_id = :pago ORDER BY registrado_en, id"),
        {"pago": pago_id},
    ).scalars()
    return estado_del_pago([str(t) for t in tipos])


def _evento(
    sesion: Session, identidad: Identidad, pago_id: UUID, tipo: str, motivo: str | None
) -> None:
    sesion.execute(
        text(
            "INSERT INTO evento_de_pago (administracion_id, pago_id, tipo, motivo, registrado_por) "
            "VALUES (:adm, :pago, :tipo, :motivo, :por)"
        ),
        {
            "adm": identidad.administracion_id,
            "pago": pago_id,
            "tipo": tipo,
            "motivo": motivo,
            "por": identidad.persona_id,
        },
    )


def registrar_en_el_libro(
    sesion: Session, identidad: Identidad, pago: PagoParaResolver, request_id: UUID
) -> dict[UUID, UUID]:
    """Un movimiento `pago` por parte, con su fila en `movimiento_de_pago`. Devuelve unidad →
    movimiento. Es el lugar donde H-021 suma el ajuste de interés, en la misma transacción."""
    cuentas = crear_cuentas_de_unidades(
        sesion, complejo_id=pago.complejo_id, unidad_ids=[p.unidad_id for p in pago.partes]
    )
    bloquear_cuentas(sesion, list(cuentas.values()))  # todas, en orden, antes de escribir
    movimientos: dict[UUID, UUID] = {}
    for parte in pago.partes:
        movimiento_id = libro_de_pagos.registrar_pago(
            sesion,
            identidad,
            cuenta_id=cuentas[parte.unidad_id],
            importe=parte.importe,
            fecha_valor=pago.fecha_de_transferencia,
            operacion_id=uuid5(_ESPACIO_DE_OPERACIONES, f"{pago.id}|{parte.id}"),
            request_id=request_id,
        )
        sesion.execute(
            text(
                "INSERT INTO movimiento_de_pago (administracion_id, pago_id, movimiento_id, "
                "papel) VALUES (:adm, :pago, :movimiento, 'pago')"
            ),
            {"adm": identidad.administracion_id, "pago": pago.id, "movimiento": movimiento_id},
        )
        movimientos[parte.unidad_id] = movimiento_id
    return movimientos


def _recordar_el_cbu(sesion: Session, identidad: Identidad, pago: PagoParaResolver) -> None:
    if pago.cbu_origen is None:
        return
    for parte in pago.partes:
        sesion.execute(
            text(
                "INSERT INTO cbu_de_unidad (administracion_id, complejo_id, unidad_id, cbu, "
                "pago_id) VALUES (:adm, :c, :unidad, :cbu, :pago) ON CONFLICT DO NOTHING"
            ),
            {
                "adm": identidad.administracion_id,
                "c": pago.complejo_id,
                "unidad": parte.unidad_id,
                "cbu": pago.cbu_origen,
                "pago": pago.id,
            },
        )


def confirmar_pago(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    pago_id: UUID,
    request_id: UUID,
) -> str:
    """Devuelve `confirmado`; un pago ya confirmado (o reimputado) lo devuelve sin escribir."""
    pago = _cargar(sesion, complejo_id, pago_id)
    _tomar_el_pago(sesion, identidad, pago_id)
    estado = _estado(sesion, pago_id)
    if estado == CONFIRMADO:
        return CONFIRMADO
    if estado != INFORMADO:
        raise Conflicto("pago", "estado")
    registrar_en_el_libro(sesion, identidad, pago, request_id)
    _recordar_el_cbu(sesion, identidad, pago)
    _evento(sesion, identidad, pago_id, CONFIRMADO, None)
    registrar(
        sesion,
        identidad,
        Accion.CONFIRMAR_PAGO_INFORMADO,
        entidad="pago_informado",
        entidad_id=pago_id,
        request_id=request_id,
        detalle={"complejo_id": complejo_id},
    )
    return CONFIRMADO


def _motivo(cuerpo: Any) -> str:
    """3 a 500 caracteres sin contar los espacios de los bordes."""
    bruto = cuerpo.get("motivo") if isinstance(cuerpo, dict) else None
    if not isinstance(bruto, str):
        raise EntradaInvalida("motivo")
    try:
        motivo = recortado_sin_control(bruto)
    except ValueError:
        raise EntradaInvalida("motivo") from None
    if not 3 <= len(motivo) <= 500:
        raise EntradaInvalida("motivo")
    return motivo


def rechazar_pago(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    pago_id: UUID,
    cuerpo: Any,
    request_id: UUID,
) -> str:
    """Deja el evento `rechazado` con su motivo, que el vecino ve; no escribe en el libro."""
    _cargar(sesion, complejo_id, pago_id)
    motivo = _motivo(cuerpo)
    _tomar_el_pago(sesion, identidad, pago_id)
    if _estado(sesion, pago_id) != INFORMADO:
        raise Conflicto("pago", "estado")
    _evento(sesion, identidad, pago_id, RECHAZADO, motivo)
    registrar(
        sesion,
        identidad,
        EventoDelPago.RECHAZAR_PAGO_INFORMADO,
        entidad="pago_informado",
        entidad_id=pago_id,
        request_id=request_id,
        detalle={"complejo_id": complejo_id},
    )
    return RECHAZADO
