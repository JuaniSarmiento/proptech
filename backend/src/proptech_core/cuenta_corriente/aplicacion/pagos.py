"""Un pago confirmado entra al libro (change 8, H-020, D-166): lo llama `pagos`, una vez por parte.

Es `registrar_credito` de tipo `pago` con R04 **a la fecha de la transferencia**: primero la deuda
que existía ese día (la que queda si no se cuentan las emisiones con período posterior), después la
deuda real que queda; lo que sobra es crédito a favor (R05). Un solo movimiento con sus
imputaciones, con la misma foto, el mismo candado y el mismo replay por `operacion_id` que los demás
créditos.
"""

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    Reloj,
    _Pedido,
    _replay,
    ahora_utc,
    imputar_pendientes,
    insertar_imputaciones,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import bloquear_cuentas, exigir_identidad
from proptech_core.cuenta_corriente.aplicacion.errores import (
    EntradaInvalida,
    exigir_transaccion,
    traducir,
)
from proptech_core.cuenta_corriente.aplicacion.lecturas import FotoDeCuenta
from proptech_core.cuenta_corriente.dominio.estado import calcular_estado
from proptech_core.cuenta_corriente.dominio.imputacion import Imputacion
from proptech_core.cuenta_corriente.dominio.pago import imputar_pago_a_la_fecha

_CERO = Dinero("0.00")


def emisiones_posteriores(sesion: Session, actual: FotoDeCuenta, fecha: date) -> frozenset[UUID]:
    """Las emisiones del edificio con período posterior a la fecha: para el pago todavía no
    existían (D-166). Las obligaciones de saldo inicial no tienen emisión y existen siempre."""
    filas = sesion.execute(
        text("SELECT id FROM emision WHERE complejo_id = :c AND periodo > :fecha"),
        {"c": actual.complejo_id, "fecha": fecha},
    ).scalars()
    return frozenset(UUID(str(f)) for f in filas)


def imputaciones_del_pago(
    sesion: Session, actual: FotoDeCuenta, fecha_valor: date, importe: Dinero
) -> list[Imputacion]:
    """Cómo se imputaría un pago de esa fecha en la cuenta tal como está (D-166, dos fases). No
    escribe: lo usan el pago y el ajuste de interés que se calcula antes de registrarlo."""
    al_dia = calcular_estado(
        actual.estado.obligaciones,
        actual.movimientos.values(),
        actual.imputaciones,
        actual.anuladas | emisiones_posteriores(sesion, actual, fecha_valor),
    )
    imputaciones, _ = imputar_pago_a_la_fecha(al_dia.deudas(), actual.estado.deudas(), importe)
    return imputaciones


def registrar_pago(
    sesion: Session,
    identidad: Identidad,
    *,
    cuenta_id: UUID,
    importe: Dinero,
    fecha_valor: date,
    operacion_id: UUID,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> UUID:
    """Devuelve el id del movimiento `pago`. Repetir el mismo `operacion_id` devuelve el mismo
    movimiento sin escribir nada (confirmar dos veces no duplica)."""
    exigir_transaccion(sesion)
    exigir_identidad(sesion, identidad)
    pedido = _Pedido(cuenta_id, "pago", importe, fecha_valor, None, None)
    previo = _replay(sesion, operacion_id, pedido, None)
    if previo is not None:
        return previo
    if not importe > _CERO:
        raise EntradaInvalida("importe")
    bloquear_cuentas(sesion, [cuenta_id])
    previo = _replay(sesion, operacion_id, pedido, None)
    if previo is not None:
        return previo
    instante = reloj()
    corrida = uuid4()
    actual = imputar_pendientes(sesion, cuenta_id, corrida, instante)
    imputaciones = imputaciones_del_pago(sesion, actual, fecha_valor, importe)
    with traducir(sesion, {"uq_mov_operacion": "operacion_id"}):
        nuevo = sesion.execute(
            text(
                "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, "
                "sentido, importe, fecha_valor, registrado_por, request_id, registrado_en, "
                "operacion_id) VALUES (:id, :adm, :complejo, :cuenta, 'pago', 'credito', "
                ":importe, :fecha, :por, :req, :en, :op) "
                "ON CONFLICT (administracion_id, operacion_id) WHERE operacion_id IS NOT NULL "
                "DO NOTHING RETURNING id"
            ),
            {
                "id": uuid4(),
                "adm": identidad.administracion_id,
                "complejo": actual.complejo_id,
                "cuenta": cuenta_id,
                "importe": importe.a_texto(),
                "fecha": fecha_valor,
                "por": identidad.persona_id,
                "req": request_id,
                "en": instante,
                "op": operacion_id,
            },
        ).scalar_one_or_none()
    if nuevo is None:  # perdió la carrera contra el mismo operacion_id
        repetido = _replay(sesion, operacion_id, pedido, None)
        if repetido is None:
            raise RuntimeError("el movimiento que ganó la carrera no se pudo leer")
        return repetido
    movimiento_id = UUID(str(nuevo))
    insertar_imputaciones(sesion, actual, movimiento_id, imputaciones, corrida, instante)
    return movimiento_id
