"""Corrección (D7, E6, R08, HU-A9): contra-asiento o crédito de corrección.

La corrección y su auditoría comparten la transacción del llamador (D9).
Los replays retornan antes de volver a registrar auditoría.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    Reloj,
    ahora_utc,
    hoy,
    imputar_pendientes,
    insertar_imputaciones,
    normalizar_motivo,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import bloquear_cuentas, exigir_identidad
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    exigir_transaccion,
    traducir,
)
from proptech_core.cuenta_corriente.dominio.imputacion import imputar

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class PedidoDeCorreccion:
    forma: Literal["contra_asiento", "credito"]
    operacion_id: UUID
    motivo: str
    movimiento_id: UUID | None = None
    obligacion_id: UUID | None = None
    importe: Dinero | None = None


def _replay(
    sesion: Session, pedido: PedidoDeCorreccion, motivo: str, complejo_id: UUID
) -> UUID | None:
    fila = sesion.execute(
        text(
            "SELECT id, complejo_id, tipo, corrige_a, obligacion_id, importe::text AS importe, "
            "motivo "
            "FROM movimiento WHERE operacion_id = :op AND administracion_id = "
            "nullif(current_setting('app.administracion_id', true), '')::uuid"
        ),
        {"op": pedido.operacion_id},
    ).one_or_none()
    if fila is None:
        return None
    if pedido.forma == "contra_asiento":
        iguales = fila.corrige_a == pedido.movimiento_id
    else:
        iguales = (
            fila.corrige_a is None
            and fila.obligacion_id == pedido.obligacion_id
            and pedido.importe is not None
            and Dinero(fila.importe) == pedido.importe
        )
    if not (
        iguales
        and fila.tipo == "correccion"
        and fila.motivo == motivo
        and fila.complejo_id == complejo_id
    ):
        raise Conflicto("operacion_id")
    return UUID(str(fila.id))


def corregir(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    pedido: PedidoDeCorreccion,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> UUID:
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    motivo = normalizar_motivo(pedido.motivo)
    if pedido.forma == "credito" and (pedido.importe is None or not pedido.importe > _CERO):
        raise EntradaInvalida("importe")
    if pedido.forma == "contra_asiento" and pedido.movimiento_id is None:
        raise EntradaInvalida("movimiento_id")
    if pedido.forma == "credito" and pedido.obligacion_id is None:
        raise EntradaInvalida("obligacion_id")
    # D5: replay antes de validar si ya está corregido.
    previo = _replay(sesion, pedido, motivo, complejo_id)
    if previo is not None:
        return previo
    instante = reloj()
    if pedido.forma == "contra_asiento":
        return _contra_asiento(
            sesion,
            identidad,
            administracion,
            complejo_id,
            pedido,
            motivo,
            request_id,
            instante,
            reloj,
        )
    return _credito(
        sesion, identidad, administracion, complejo_id, pedido, motivo, request_id, instante, reloj
    )


def _anulada(sesion: Session, emision_id: UUID | None) -> bool:
    if emision_id is None:
        return False
    return (
        sesion.execute(
            text("SELECT 1 FROM evento_de_emision WHERE emision_id = :e AND tipo = 'anulada'"),
            {"e": emision_id},
        ).one_or_none()
        is not None
    )


def _insertar(sesion: Session, valores: dict[str, object]) -> UUID | None:
    with traducir(
        sesion,
        {"uq_mov_corrige_a": "movimiento_id", "uq_mov_operacion": "operacion_id"},
    ):
        nuevo = sesion.execute(
            text(
                "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, "
                "sentido, "
                "importe, fecha_valor, registrado_por, request_id, registrado_en, operacion_id, "
                "obligacion_id, corrige_a, tipo_corregido, motivo) VALUES (:id, :adm, :complejo, "
                ":cuenta, 'correccion', :sentido, :importe, :fecha, :por, :req, :en, :op, :obl, "
                ":corrige, :tipo_corregido, :motivo) "
                "ON CONFLICT (administracion_id, operacion_id) WHERE operacion_id IS NOT NULL "
                "DO NOTHING RETURNING id"
            ),
            valores,
        ).scalar_one_or_none()
    return None if nuevo is None else UUID(str(nuevo))


def _contra_asiento(
    sesion: Session,
    identidad: Identidad,
    administracion: UUID,
    complejo_id: UUID,
    pedido: PedidoDeCorreccion,
    motivo: str,
    request_id: UUID,
    instante: datetime,
    reloj: Reloj,
) -> UUID:
    blanco = sesion.execute(
        text(
            "SELECT m.id, m.cuenta_id, m.complejo_id, m.tipo, m.sentido, "
            "m.importe::text AS importe, "
            "m.emision_id, m.corrige_a, o.emision_id AS emision_de_la_obligacion FROM movimiento m "
            "LEFT JOIN obligacion o ON o.id = m.obligacion_id "
            "AND o.administracion_id = m.administracion_id "
            "WHERE m.id = :id"
        ),
        {"id": pedido.movimiento_id},
    ).one_or_none()
    if blanco is None or blanco.complejo_id != complejo_id:
        raise NoEncontrado
    bloquear_cuentas(sesion, [blanco.cuenta_id])
    # CX-01, E4: resolver la operación que pudo aparecer durante la espera, antes de validar.
    previo = _replay(sesion, pedido, motivo, complejo_id)
    if previo is not None:
        return previo
    # Bajo el candado (RC-12): la base no distingue el blanco; la aplicación sí.
    if blanco.tipo == "correccion" and blanco.sentido == "debito":
        raise Conflicto("movimiento_id")
    if _anulada(sesion, blanco.emision_id) or _anulada(sesion, blanco.emision_de_la_obligacion):
        raise Conflicto("movimiento_id")
    ya = sesion.execute(
        text("SELECT 1 FROM movimiento WHERE corrige_a = :id"), {"id": blanco.id}
    ).one_or_none()
    if ya is not None:
        raise Conflicto("movimiento_id")
    imputar_pendientes(sesion, blanco.cuenta_id, uuid4(), instante)
    nuevo = _insertar(
        sesion,
        {
            "id": uuid4(),
            "adm": administracion,
            "complejo": complejo_id,
            "cuenta": blanco.cuenta_id,
            "sentido": "credito" if blanco.sentido == "debito" else "debito",
            "importe": blanco.importe,
            "fecha": hoy(reloj),
            "por": identidad.persona_id,
            "req": request_id,
            "en": instante,
            "op": pedido.operacion_id,
            "obl": None,
            "corrige": blanco.id,
            "tipo_corregido": blanco.tipo,
            "motivo": motivo,
        },
    )
    if nuevo is None:
        repetido = _replay(sesion, pedido, motivo, complejo_id)
        if repetido is None:
            raise RuntimeError("el movimiento que ganó la carrera no se pudo leer")
        return repetido
    _auditar(sesion, identidad, complejo_id, pedido, nuevo, request_id)
    return nuevo


def _credito(
    sesion: Session,
    identidad: Identidad,
    administracion: UUID,
    complejo_id: UUID,
    pedido: PedidoDeCorreccion,
    motivo: str,
    request_id: UUID,
    instante: datetime,
    reloj: Reloj,
) -> UUID:
    obligacion = sesion.execute(
        text("SELECT id, cuenta_id, complejo_id, emision_id FROM obligacion WHERE id = :id"),
        {"id": pedido.obligacion_id},
    ).one_or_none()
    if obligacion is None or obligacion.complejo_id != complejo_id:
        raise NoEncontrado
    bloquear_cuentas(sesion, [obligacion.cuenta_id])
    previo = _replay(sesion, pedido, motivo, complejo_id)
    if previo is not None:
        return previo
    if _anulada(sesion, obligacion.emision_id):
        raise Conflicto("obligacion_id")
    corrida = uuid4()
    actual = imputar_pendientes(sesion, obligacion.cuenta_id, corrida, instante)
    if pedido.importe is None:
        raise EntradaInvalida("importe")
    imputaciones, _ = imputar(actual.estado.deudas(), pedido.importe)  # R04 (D-086)
    nuevo = _insertar(
        sesion,
        {
            "id": uuid4(),
            "adm": administracion,
            "complejo": complejo_id,
            "cuenta": obligacion.cuenta_id,
            "sentido": "credito",
            "importe": pedido.importe.a_texto(),
            "fecha": hoy(reloj),
            "por": identidad.persona_id,
            "req": request_id,
            "en": instante,
            "op": pedido.operacion_id,
            "obl": obligacion.id,
            "corrige": None,
            "tipo_corregido": None,
            "motivo": motivo,
        },
    )
    if nuevo is None:
        repetido = _replay(sesion, pedido, motivo, complejo_id)
        if repetido is None:
            raise RuntimeError("el movimiento que ganó la carrera no se pudo leer")
        return repetido
    insertar_imputaciones(sesion, actual, nuevo, imputaciones, corrida, instante)
    _auditar(sesion, identidad, complejo_id, pedido, nuevo, request_id)
    return nuevo


def _auditar(
    sesion: Session,
    identidad: Identidad,
    complejo_id: UUID,
    pedido: PedidoDeCorreccion,
    movimiento_id: UUID,
    request_id: UUID,
) -> None:
    registrar(
        sesion,
        identidad,
        Accion.CORREGIR_MOVIMIENTO,
        entidad="movimiento",
        entidad_id=movimiento_id,
        request_id=request_id,
        detalle={
            "complejo_id": complejo_id,
            "forma": pedido.forma,
            "corrige": pedido.movimiento_id
            if pedido.forma == "contra_asiento"
            else pedido.obligacion_id,
        },
    )
