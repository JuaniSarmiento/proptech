"""Créditos (lo llama el 8) e `imputar_pendientes` (D5, D6, D8, E16)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.cuenta_corriente.aplicacion.cuentas import bloquear_cuentas, exigir_identidad
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    exigir_transaccion,
    traducir,
)
from proptech_core.cuenta_corriente.aplicacion.lecturas import FotoDeCuenta, foto
from proptech_core.cuenta_corriente.dominio.estado import TIPOS_DE_DESTINO_FIJO
from proptech_core.cuenta_corriente.dominio.imputacion import Destino, Imputacion, imputar

_CERO = Dinero("0.00")

#: D3: `correccion` entra por `corregir`, `saldo_inicial` es del 4c.
TIPOS_DE_CREDITO = frozenset(
    {"pago", "condonacion", "ajuste_de_interes", "bonificacion", "baja_de_deuda"}
)

Reloj = Callable[[], datetime]


def ahora_utc() -> datetime:
    return datetime.now(UTC)


def hoy(reloj: Reloj) -> date:
    """La misma regla que `complejos` (hoy en Mendoza); el import cruzado lo prohíbe D0."""
    instante = reloj()
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ValueError("el reloj debe devolver un instante con zona horaria")
    return instante.astimezone(ZoneInfo("America/Argentina/Mendoza")).date()


def normalizar_motivo(motivo: str) -> str:
    try:
        limpio = recortado_sin_control(motivo)
    except ValueError:
        raise EntradaInvalida("motivo") from None
    if len(limpio) > 500:
        raise EntradaInvalida("motivo")
    return limpio


def insertar_imputaciones(
    sesion: Session,
    actual: FotoDeCuenta,
    movimiento_id: UUID,
    imputaciones: Sequence[Imputacion],
    corrida_id: UUID,
    registrada_en: datetime,
) -> None:
    for i in imputaciones:  # el orden de la lista es el de `orden` (secuencia, E7)
        sesion.execute(
            text(
                "INSERT INTO imputacion (id, administracion_id, complejo_id, cuenta_id, "
                "movimiento_id, sentido_del_movimiento, obligacion_id, componente, importe, "
                "corrida_id, registrada_en) SELECT :id, "
                "nullif(current_setting('app.administracion_id', true), '')::uuid, :complejo, "
                ":cuenta, :movimiento, 'credito', :obligacion, :componente, :importe, :corrida, :en"
            ),
            {
                "id": uuid4(),
                "complejo": actual.complejo_id,
                "cuenta": actual.cuenta_id,
                "movimiento": movimiento_id,
                "obligacion": i.obligacion_id,
                "componente": i.componente.value,
                "importe": i.importe.a_texto(),
                "corrida": corrida_id,
                "en": registrada_en,
            },
        )


def imputar_pendientes(
    sesion: Session, cuenta_id: UUID, corrida_id: UUID, registrada_en: datetime
) -> FotoDeCuenta:
    """Con la cuenta ya bloqueada: imputa el crédito a favor aplicable, del más viejo al más nuevo
    (`fecha_valor`, `registrado_en`, `id`). Un crédito de destino fijo conserva su destino; si está
    retenido (destino que no cuenta o sin residual), se saltea hasta su reversión (R37, E16)."""
    actual = foto(sesion, cuenta_id)
    creditos = sorted(
        (
            actual.movimientos[m]
            for m, favor in actual.estado.a_favor_por_credito.items()
            if favor > _CERO and m not in actual.estado.retenidos
        ),
        key=lambda m: (m.fecha_valor, m.registrado_en, str(m.id)),
    )
    for m in creditos:
        favor = actual.estado.a_favor_por_credito[m.id]
        destino = None
        if m.tipo in TIPOS_DE_DESTINO_FIJO:
            if m.obligacion_id is None or m.componente is None:
                continue
            # Sin tope por el residual del destino: no es alcanzable (RB4B-04). Un crédito de
            # destino fijo sólo tiene crédito a favor si una fila suya topó contra lo que se debe
            # en su destino, y entonces ese residual es cero y queda retenido (paso 5 de D8).
            destino = Destino(m.obligacion_id, m.componente)
        if not actual.estado.deudas() or not favor > _CERO:
            continue
        imputaciones, _ = imputar(actual.estado.deudas(), favor, destino)
        if imputaciones:
            insertar_imputaciones(sesion, actual, m.id, imputaciones, corrida_id, registrada_en)
            actual = foto(sesion, cuenta_id)
    return actual


@dataclass(frozen=True)
class _Pedido:
    cuenta_id: UUID
    tipo: str
    importe: Dinero
    fecha_valor: date
    obligacion_id: UUID | None
    componente: str | None


def _replay(
    sesion: Session, operacion_id: UUID, pedido: _Pedido, complejo_id: UUID | None
) -> UUID | None:
    fila = sesion.execute(
        text(
            "SELECT id, cuenta_id, complejo_id, tipo, sentido, importe::text AS importe, "
            "fecha_valor, obligacion_id, componente FROM movimiento "
            "WHERE operacion_id = :op AND administracion_id = "
            "nullif(current_setting('app.administracion_id', true), '')::uuid"
        ),
        {"op": operacion_id},
    ).one_or_none()
    if fila is None:
        return None
    iguales = (
        fila.cuenta_id == pedido.cuenta_id
        and fila.tipo == pedido.tipo
        and fila.sentido == "credito"
        and Dinero(fila.importe) == pedido.importe
        and fila.fecha_valor == pedido.fecha_valor
        and fila.obligacion_id == pedido.obligacion_id
        and fila.componente == pedido.componente
        and (complejo_id is None or fila.complejo_id == complejo_id)
    )
    if not iguales:
        raise Conflicto("operacion_id")
    return UUID(str(fila.id))


def registrar_credito(
    sesion: Session,
    identidad: Identidad,
    *,
    cuenta_id: UUID,
    tipo: str,
    importe: Dinero,
    fecha_valor: date,
    operacion_id: UUID,
    destino: Destino | None,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> UUID:
    exigir_transaccion(sesion)
    exigir_identidad(sesion, identidad)
    pedido = _Pedido(
        cuenta_id,
        tipo,
        importe,
        fecha_valor,
        destino.obligacion_id if destino else None,
        destino.componente.value if destino else None,
    )
    # D5: primero el replay, antes de validar o imputar pendientes.
    previo = _replay(sesion, operacion_id, pedido, None)
    if previo is not None:
        return previo
    if tipo not in TIPOS_DE_CREDITO:
        raise EntradaInvalida("tipo")
    if not importe > _CERO:
        raise EntradaInvalida("importe")
    if (tipo in TIPOS_DE_DESTINO_FIJO) != (destino is not None):
        raise EntradaInvalida("destino")
    instante = reloj()
    bloquear_cuentas(sesion, [cuenta_id])  # NoEncontrado si la cuenta no existe o es ajena
    if destino is not None:
        _exigir_obligacion_de_la_cuenta(sesion, cuenta_id, destino.obligacion_id)
    corrida = uuid4()
    actual = imputar_pendientes(sesion, cuenta_id, corrida, instante)
    imputaciones, _ = imputar(actual.estado.deudas(), importe, destino)  # E16: antes del INSERT
    with traducir(sesion, {"uq_mov_operacion": "operacion_id"}):
        nuevo = sesion.execute(
            text(
                "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, "
                "sentido, importe, fecha_valor, registrado_por, request_id, registrado_en, "
                "operacion_id, obligacion_id, componente) VALUES (:id, :adm, :complejo, :cuenta, "
                ":tipo, 'credito', :importe, :fecha, :por, :req, :en, :op, :obl, :comp) "
                "ON CONFLICT (administracion_id, operacion_id) WHERE operacion_id IS NOT NULL "
                "DO NOTHING RETURNING id"
            ),
            {
                "id": uuid4(),
                "adm": identidad.administracion_id,
                "complejo": actual.complejo_id,
                "cuenta": cuenta_id,
                "tipo": tipo,
                "importe": importe.a_texto(),
                "fecha": fecha_valor,
                "por": identidad.persona_id,
                "req": request_id,
                "en": instante,
                "op": operacion_id,
                "obl": pedido.obligacion_id,
                "comp": pedido.componente,
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


def _exigir_obligacion_de_la_cuenta(sesion: Session, cuenta_id: UUID, obligacion_id: UUID) -> None:
    """D3, RB4B-05: la obligación de destino inexistente, ajena o de otra cuenta es `NoEncontrado`,
    antes de escribir; la que existe y no puede absorber el crédito es `destino` (E16)."""
    existe = sesion.execute(
        text("SELECT 1 FROM obligacion WHERE id = :o AND cuenta_id = :c"),
        {"o": obligacion_id, "c": cuenta_id},
    ).one_or_none()
    if existe is None:
        raise NoEncontrado


def exigir_cuenta(sesion: Session, cuenta_id: UUID) -> None:
    existe = sesion.execute(
        text("SELECT 1 FROM cuenta WHERE id = :c"), {"c": cuenta_id}
    ).one_or_none()
    if existe is None:
        raise NoEncontrado
