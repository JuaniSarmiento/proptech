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
from proptech_core.complejos.aplicacion.lectura import cargar_unidad
from proptech_core.cuenta_corriente.aplicacion import pagos as libro_de_pagos
from proptech_core.cuenta_corriente.aplicacion.ajuste_de_interes import ajustar_el_interes
from proptech_core.cuenta_corriente.aplicacion.cuentas import (
    bloquear_cuentas,
    crear_cuentas_de_unidades,
)
from proptech_core.cuenta_corriente.aplicacion.reversion_de_pago import (
    reimputar_desde,
    revertir_pago,
)
from proptech_core.pagos.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado
from proptech_core.pagos.dominio.estado import INFORMADO, estado_del_pago

#: Fijo: de él sale el `operacion_id` de cada parte (confirmar dos veces es una repetición).
_ESPACIO_DE_OPERACIONES = UUID("5d1c3a9e-0b7f-4c52-9a4e-8e2f6b1d7c30")

CONFIRMADO = "confirmado"
RECHAZADO = "rechazado"
REVERTIDO = "revertido"
REIMPUTADO = "reimputado"


@dataclass(frozen=True)
class ParteDelPago:
    id: UUID
    unidad_id: UUID
    importe: Dinero


@dataclass(frozen=True)
class PagoEnElLibro:
    #: unidad → movimiento `pago`.
    movimientos: dict[UUID, UUID]
    #: Lo que correspondía ajustar de interés y no entró en su destino (E7); `None` si todo entró.
    ajuste_sin_destino: Dinero | None


@dataclass(frozen=True)
class Confirmacion:
    estado: str
    ajuste_sin_destino: Dinero | None = None


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


def _fila_del_pago(
    sesion: Session, identidad: Identidad, pago_id: UUID, movimiento_id: UUID, papel: str
) -> None:
    sesion.execute(
        text(
            "INSERT INTO movimiento_de_pago (administracion_id, pago_id, movimiento_id, "
            "papel) VALUES (:adm, :pago, :movimiento, :papel)"
        ),
        {
            "adm": identidad.administracion_id,
            "pago": pago_id,
            "movimiento": movimiento_id,
            "papel": papel,
        },
    )


def registrar_en_el_libro(
    sesion: Session, identidad: Identidad, pago: PagoParaResolver, request_id: UUID
) -> PagoEnElLibro:
    """Por cada parte, primero el ajuste del interés que se cobró de más (E7) y después el
    movimiento `pago`, cada uno con su fila en `movimiento_de_pago` y todos en la transacción del
    llamador. Los ajustes van antes para que R04 no use el pago en un interés que se compensa."""
    cuentas = crear_cuentas_de_unidades(
        sesion, complejo_id=pago.complejo_id, unidad_ids=[p.unidad_id for p in pago.partes]
    )
    bloquear_cuentas(sesion, list(cuentas.values()))  # todas, en orden, antes de escribir
    movimientos: dict[UUID, UUID] = {}
    sin_destino = Dinero("0.00")
    for parte in pago.partes:
        operacion = uuid5(_ESPACIO_DE_OPERACIONES, f"{pago.id}|{parte.id}")
        ajuste = ajustar_el_interes(
            sesion,
            identidad,
            cuenta_id=cuentas[parte.unidad_id],
            importe=parte.importe,
            fecha_valor=pago.fecha_de_transferencia,
            operacion_base=operacion,
            request_id=request_id,
        )
        for registrado in ajuste.registrados:
            _fila_del_pago(
                sesion, identidad, pago.id, registrado.movimiento_id, "ajuste_de_interes"
            )
        sin_destino = sin_destino + ajuste.sin_destino
        movimiento_id = libro_de_pagos.registrar_pago(
            sesion,
            identidad,
            cuenta_id=cuentas[parte.unidad_id],
            importe=parte.importe,
            fecha_valor=pago.fecha_de_transferencia,
            operacion_id=operacion,
            request_id=request_id,
        )
        _fila_del_pago(sesion, identidad, pago.id, movimiento_id, "pago")
        movimientos[parte.unidad_id] = movimiento_id
    return PagoEnElLibro(movimientos, sin_destino if sin_destino > Dinero("0.00") else None)


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
) -> Confirmacion:
    """Devuelve `confirmado` (con lo que no entró del ajuste de interés, si hubo); un pago ya
    confirmado (o reimputado) lo devuelve sin escribir."""
    pago = _cargar(sesion, complejo_id, pago_id)
    _tomar_el_pago(sesion, identidad, pago_id)
    estado = _estado(sesion, pago_id)
    if estado == CONFIRMADO:
        return Confirmacion(CONFIRMADO)
    if estado != INFORMADO:
        raise Conflicto("pago", "estado")
    en_el_libro = registrar_en_el_libro(sesion, identidad, pago, request_id)
    _recordar_el_cbu(sesion, identidad, pago)
    _evento(sesion, identidad, pago_id, CONFIRMADO, None)
    registrar(
        sesion,
        identidad,
        Accion.CONFIRMAR_PAGO_INFORMADO,
        entidad="pago_informado",
        entidad_id=pago_id,
        request_id=request_id,
        detalle=(
            {"complejo_id": complejo_id}
            if en_el_libro.ajuste_sin_destino is None
            else {
                "complejo_id": complejo_id,
                "ajuste_sin_destino": True,
            }
        ),
    )
    return Confirmacion(CONFIRMADO, en_el_libro.ajuste_sin_destino)


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


def _movimientos_del_pago(sesion: Session, pago_id: UUID) -> tuple[list[UUID], list[UUID]]:
    """Lo que el pago dejó en el libro, según `movimiento_de_pago`: los créditos de sus partes (el
    `pago` o el `reimputacion`) y, aparte, sus ajustes de interés. Cuáles siguen vigentes lo decide
    el libro, bajo el candado de cada cuenta."""
    filas = sesion.execute(
        text(
            "SELECT movimiento_id, papel FROM movimiento_de_pago WHERE pago_id = :pago "
            "AND papel IN ('pago', 'reimputacion', 'ajuste_de_interes') ORDER BY id"
        ),
        {"pago": pago_id},
    ).all()
    partes = [UUID(str(f.movimiento_id)) for f in filas if f.papel != "ajuste_de_interes"]
    ajustes = [UUID(str(f.movimiento_id)) for f in filas if f.papel == "ajuste_de_interes"]
    return partes, ajustes


def revertir_pago_confirmado(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    pago_id: UUID,
    cuerpo: Any,
    request_id: UUID,
) -> str:
    """Revierte un pago confirmado (H-022): el pago (404), el motivo (422), el estado (409).

    El libro bloquea las cuentas de todas las partes y escribe las reversiones (`reversion_de_pago`
    por parte, el contra-asiento de cada ajuste y, por P29, el `interes_por_reversion`), cada una
    con su fila en `movimiento_de_pago`; después, el evento `revertido` con su motivo y la
    auditoría. Todo en la transacción del llamador: si falla un paso no queda ninguno."""
    pago = _cargar(sesion, complejo_id, pago_id)
    motivo = _motivo(cuerpo)
    _tomar_el_pago(sesion, identidad, pago_id)
    if _estado(sesion, pago_id) != CONFIRMADO:
        raise Conflicto("pago", "estado")
    partes, ajustes = _movimientos_del_pago(sesion, pago_id)
    for reversion in revertir_pago(
        sesion,
        identidad,
        pago_id=pago_id,
        creditos=partes,
        ajustes=ajustes,
        fecha_de_transferencia=pago.fecha_de_transferencia,
        motivo=motivo,
        request_id=request_id,
    ):
        _fila_del_pago(sesion, identidad, pago_id, reversion.movimiento_id, reversion.papel)
    _evento(sesion, identidad, pago_id, REVERTIDO, motivo)
    registrar(
        sesion,
        identidad,
        EventoDelPago.REVERTIR_PAGO_INFORMADO,
        entidad="pago_informado",
        entidad_id=pago_id,
        request_id=request_id,
        detalle={"complejo_id": complejo_id},
    )
    return REVERTIDO


def _unidad_del_cuerpo(cuerpo: Any, campo: str) -> UUID:
    bruto = cuerpo.get(campo) if isinstance(cuerpo, dict) else None
    if not isinstance(bruto, str):
        raise EntradaInvalida(campo)
    try:
        return UUID(bruto)
    except ValueError:
        raise EntradaInvalida(campo) from None


def reimputar_pago_confirmado(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    pago_id: UUID,
    cuerpo: Any,
    request_id: UUID,
) -> str:
    """Reimputa lo que un pago confirmado tiene en una unidad a otra del edificio (H-023, R25).

    Orden: el pago (404), el motivo (422), la unidad de destino (404), la misma unidad (422), el
    estado (409) y que `desde_unidad_id` tenga algo vigente del pago (422). En la transacción del
    llamador y bajo el candado del pago: el origen se deshace como al revertir (H-022) y el destino
    se acredita como al confirmar (D-166): `reimputacion` crédito a la fecha de la transferencia,
    con R04 y con su ajuste de interés (H-021), enlazado al débito del origen. Si falla un paso no
    queda ninguno."""
    pago = _cargar(sesion, complejo_id, pago_id)
    motivo = _motivo(cuerpo)
    desde = _unidad_del_cuerpo(cuerpo, "desde_unidad_id")
    hacia = _unidad_del_cuerpo(cuerpo, "hacia_unidad_id")
    destino = cargar_unidad(sesion, hacia)
    if destino is None or destino.complejo_id != complejo_id:
        raise NoEncontrado
    if desde == hacia:
        raise EntradaInvalida("hacia_unidad_id")
    _tomar_el_pago(sesion, identidad, pago_id)
    if _estado(sesion, pago_id) != CONFIRMADO:
        raise Conflicto("pago", "estado")
    cuenta_destino = crear_cuentas_de_unidades(sesion, complejo_id=complejo_id, unidad_ids=[hacia])[
        hacia
    ]
    partes, ajustes = _movimientos_del_pago(sesion, pago_id)
    escritos = reimputar_desde(
        sesion,
        identidad,
        pago_id=pago_id,
        creditos=partes,
        ajustes=ajustes,
        desde_unidad_id=desde,
        cuenta_destino=cuenta_destino,
        fecha_de_transferencia=pago.fecha_de_transferencia,
        motivo=motivo,
        request_id=request_id,
    )
    debitos = [e for e in escritos if e.papel == "reimputacion"]
    if not debitos:
        raise EntradaInvalida("desde_unidad_id")
    for escrito in escritos:
        _fila_del_pago(sesion, identidad, pago_id, escrito.movimiento_id, escrito.papel)
    for debito in debitos:
        importe = debito.importe or Dinero("0.00")
        operacion = uuid5(_ESPACIO_DE_OPERACIONES, f"{pago_id}|{debito.movimiento_id}")
        ajuste = ajustar_el_interes(
            sesion,
            identidad,
            cuenta_id=cuenta_destino,
            importe=importe,
            fecha_valor=pago.fecha_de_transferencia,
            operacion_base=operacion,
            request_id=request_id,
        )
        for registrado in ajuste.registrados:
            _fila_del_pago(
                sesion, identidad, pago_id, registrado.movimiento_id, "ajuste_de_interes"
            )
        credito = libro_de_pagos.registrar_pago(
            sesion,
            identidad,
            cuenta_id=cuenta_destino,
            importe=importe,
            fecha_valor=pago.fecha_de_transferencia,
            operacion_id=operacion,
            request_id=request_id,
            tipo="reimputacion",
            enlazado_a=debito.movimiento_id,
            motivo=motivo,
        )
        _fila_del_pago(sesion, identidad, pago_id, credito, "reimputacion")
    _evento(sesion, identidad, pago_id, REIMPUTADO, motivo)
    registrar(
        sesion,
        identidad,
        EventoDelPago.REIMPUTAR_PAGO_INFORMADO,
        entidad="pago_informado",
        entidad_id=pago_id,
        request_id=request_id,
        detalle={"complejo_id": complejo_id},
    )
    return CONFIRMADO
