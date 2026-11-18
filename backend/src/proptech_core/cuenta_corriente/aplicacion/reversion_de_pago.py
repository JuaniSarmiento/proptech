"""Revertir en el libro los movimientos de un pago confirmado (change 8, H-022, R18, D-163 P29).

Un pago que el banco devuelve tiene que dejar la cuenta como si nunca hubiera entrado. Por cada
cuenta del pago, con los candados ya tomados por el llamador y en su transacción:

1. un `reversion_de_pago` (débito) que corrige el movimiento vigente de esa parte, por su mismo
   importe y con el motivo: el par deja de contar y sus imputaciones con él (`_excluidos`);
2. un contra-asiento (`correccion` débito) por cada `ajuste_de_interes` que se registró con el pago
   (H-021): el interés que el ajuste compensaba vuelve a contar entero;
3. P29: el interés de los días ya cobrados con el pago adentro. Cada interés de una emisión
   posterior a la fecha de la transferencia se recalcula sobre sus mismos tramos, con su tasa y su
   forma guardadas, con la base que queda **sin** el pago. Si lo recalculado supera lo que la cuenta
   registra neto del interés (el interés más sus complementos menos sus ajustes que cuentan), la
   diferencia es un `interes_por_reversion` enlazado a ese interés. La cuenta queda igual al
   centavo que la de quien nunca pagó.

Reimputar (H-023, R25) usa el mismo trabajo por cuenta para el origen, con un `reimputacion`
débito en vez del `reversion_de_pago` (`reimputar_desde`); el destino lo acredita el llamador.

Un `interes_por_reversion` no genera interés (la base de capital nunca suma el componente interés,
R03) y deja de contar si su interés deja de contar (D-085).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4, uuid5

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.ajuste_de_interes import tramos_guardados
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    Reloj,
    ahora_utc,
    hoy,
    imputar_pendientes,
    normalizar_motivo,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import bloquear_cuentas, exigir_identidad
from proptech_core.cuenta_corriente.aplicacion.errores import (
    NoEncontrado,
    exigir_transaccion,
    traducir,
)
from proptech_core.cuenta_corriente.aplicacion.lecturas import FotoDeCuenta, foto
from proptech_core.cuenta_corriente.aplicacion.pagos import emisiones_posteriores
from proptech_core.cuenta_corriente.dominio.intereses import (
    base_de_capital,
    interes_de_los_tramos,
)

_CERO = Dinero("0.00")
_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))
#: Fijo: de él sale el `operacion_id` de cada movimiento de la reversión (repetir no duplica).
_ESPACIO_DE_REVERSIONES = UUID("e7a2c9d4-1f3b-4d68-8a5e-4b9c0d2f6a17")

Papel = Literal["reversion_de_pago", "interes_por_reversion", "reimputacion"]


@dataclass(frozen=True)
class MovimientoDeReversion:
    movimiento_id: UUID
    papel: Papel
    #: El importe, para el `reimputacion` débito: lo que el destino recibe (H-023).
    importe: Dinero | None = None


def _insertar(
    sesion: Session,
    identidad: Identidad,
    actual: FotoDeCuenta,
    *,
    tipo: str,
    sentido: str,
    importe: Dinero,
    fecha_valor: date,
    operacion_id: UUID,
    motivo: str,
    request_id: UUID,
    instante: datetime,
    obligacion_id: UUID | None = None,
    componente: str | None = None,
    corrige_a: UUID | None = None,
    tipo_corregido: str | None = None,
    enlazado_a: UUID | None = None,
) -> UUID:
    nuevo = uuid4()
    with traducir(
        sesion, {"uq_mov_corrige_a": "movimiento_id", "uq_mov_operacion": "operacion_id"}
    ):
        sesion.execute(
            text(
                "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, "
                "sentido, importe, fecha_valor, registrado_por, request_id, registrado_en, "
                "operacion_id, obligacion_id, componente, corrige_a, tipo_corregido, enlazado_a, "
                "motivo) VALUES (:id, :adm, :complejo, :cuenta, :tipo, :sentido, :importe, "
                ":fecha, :por, :req, :en, :op, :obl, :comp, :corrige, :tipo_corregido, :enlace, "
                ":motivo)"
            ),
            {
                "id": nuevo,
                "adm": identidad.administracion_id,
                "complejo": actual.complejo_id,
                "cuenta": actual.cuenta_id,
                "tipo": tipo,
                "sentido": sentido,
                "importe": importe.a_texto(),
                "fecha": fecha_valor,
                "por": identidad.persona_id,
                "req": request_id,
                "en": instante,
                "op": operacion_id,
                "obl": obligacion_id,
                "comp": componente,
                "corrige": corrige_a,
                "tipo_corregido": tipo_corregido,
                "enlace": enlazado_a,
                "motivo": motivo,
            },
        )
    return nuevo


def _cuentas_de(sesion: Session, movimiento_ids: Sequence[UUID]) -> dict[UUID, UUID]:
    """movimiento → cuenta. Un id que la RLS esconde o que no existe es un 404."""
    filas = sesion.execute(
        text("SELECT id, cuenta_id FROM movimiento WHERE id = ANY(:ids)").bindparams(_IDS),
        {"ids": list(movimiento_ids)},
    ).all()
    cuentas = {UUID(str(f.id)): UUID(str(f.cuenta_id)) for f in filas}
    if set(cuentas) != set(movimiento_ids):
        raise NoEncontrado
    return cuentas


def _sumar(montos: Sequence[Dinero]) -> Dinero:
    total = _CERO
    for monto in montos:
        total = total + monto
    return total


def _intereses_por_reversion(
    sesion: Session,
    identidad: Identidad,
    despues: FotoDeCuenta,
    *,
    pago_id: UUID,
    fecha_de_transferencia: date,
    motivo: str,
    request_id: UUID,
    instante: datetime,
) -> list[MovimientoDeReversion]:
    """P29: lo que el interés cobró de menos por tener el pago adentro, con la cuenta ya sin él."""
    cuentan = despues.estado.movimientos_que_cuentan
    posteriores = emisiones_posteriores(sesion, despues, fecha_de_transferencia)
    intereses = sorted(
        (
            m
            for m in despues.movimientos.values()
            if m.tipo == "interes"
            and m.id in cuentan
            and m.emision_id in posteriores
            and m.obligacion_id is not None
        ),
        key=lambda m: (m.fecha_valor, str(m.id)),
    )
    if not intereses:
        return []
    tramos = tramos_guardados(sesion, despues.cuenta_id, [m.id for m in intereses])
    por_id = {o.id: o for o in despues.estado.obligaciones}
    registrados: list[MovimientoDeReversion] = []
    for interes in intereses:
        if interes.obligacion_id is None or interes.id not in tramos:
            continue  # sin tramos guardados (el interés importado, E17) no hay sobre qué recalcular
        guardados, gracia = tramos[interes.id]
        recalculado = interes_de_los_tramos(
            guardados,
            base_de_capital(
                por_id[interes.obligacion_id], despues.estado, despues.movimientos, gracia
            ),
        )
        enlazados = [
            m
            for m in despues.movimientos.values()
            if m.enlazado_a == interes.id and m.id in cuentan
        ]
        registrado = (
            interes.importe
            + _sumar([m.importe for m in enlazados if m.tipo == "interes_por_reversion"])
            - _sumar([m.importe for m in enlazados if m.tipo == "ajuste_de_interes"])
        )
        diferencia = recalculado - registrado
        if not diferencia > _CERO:
            continue
        movimiento_id = _insertar(
            sesion,
            identidad,
            despues,
            tipo="interes_por_reversion",
            sentido="debito",
            importe=diferencia,
            fecha_valor=interes.fecha_valor,
            operacion_id=uuid5(_ESPACIO_DE_REVERSIONES, f"{pago_id}|interes|{interes.id}"),
            motivo=motivo,
            request_id=request_id,
            instante=instante,
            obligacion_id=interes.obligacion_id,
            componente="interes",
            enlazado_a=interes.id,
        )
        registrados.append(MovimientoDeReversion(movimiento_id, "interes_por_reversion"))
    return registrados


def _revertir_en_la_cuenta(
    sesion: Session,
    identidad: Identidad,
    cuenta_id: UUID,
    creditos: Sequence[UUID],
    ajustes: Sequence[UUID],
    *,
    papel_del_debito: Literal["reversion_de_pago", "reimputacion"],
    pago_id: UUID,
    fecha_de_transferencia: date,
    motivo: str,
    request_id: UUID,
    reloj: Reloj,
    instante: datetime,
) -> list[MovimientoDeReversion]:
    """Lo de una cuenta, con su candado ya tomado: el débito que corrige cada crédito vigente (de
    tipo `reversion_de_pago` o `reimputacion`), el contra-asiento de cada ajuste que cuenta y el
    interés por reversión de P29. Al reimputar, sin ningún crédito vigente no escribe nada y
    devuelve `[]`; al revertir sigue con los ajustes que queden."""
    imputar_pendientes(sesion, cuenta_id, uuid4(), instante)
    antes = foto(sesion, cuenta_id)
    corregidos = {m.corrige_a for m in antes.movimientos.values() if m.corrige_a is not None}
    vigentes = [
        antes.movimientos[c]
        for c in creditos
        if c not in corregidos and antes.movimientos[c].sentido == "credito"
    ]
    if not vigentes and papel_del_debito == "reimputacion":
        return []  # nada vigente que mover: reimputar lo traduce en un 422 (revertir sigue)
    registrados: list[MovimientoDeReversion] = []
    for blanco in vigentes:
        nuevo = _insertar(
            sesion,
            identidad,
            antes,
            tipo=papel_del_debito,
            sentido="debito",
            importe=blanco.importe,
            fecha_valor=hoy(reloj),
            operacion_id=uuid5(_ESPACIO_DE_REVERSIONES, f"{pago_id}|{blanco.id}"),
            motivo=motivo,
            request_id=request_id,
            instante=instante,
            corrige_a=blanco.id,
            tipo_corregido=blanco.tipo,
        )
        registrados.append(MovimientoDeReversion(nuevo, papel_del_debito, blanco.importe))
    for ajuste in ajustes:
        blanco = antes.movimientos[ajuste]
        if blanco.id in corregidos or blanco.id not in antes.estado.movimientos_que_cuentan:
            continue  # ya corregido, o ya no cuenta (su interés se anuló): nada que restaurar
        nuevo = _insertar(
            sesion,
            identidad,
            antes,
            tipo="correccion",
            sentido="debito",
            importe=blanco.importe,
            fecha_valor=hoy(reloj),
            operacion_id=uuid5(_ESPACIO_DE_REVERSIONES, f"{pago_id}|{blanco.id}"),
            motivo=motivo,
            request_id=request_id,
            instante=instante,
            corrige_a=blanco.id,
            tipo_corregido=blanco.tipo,
        )
        registrados.append(MovimientoDeReversion(nuevo, "reversion_de_pago"))
    registrados.extend(
        _intereses_por_reversion(
            sesion,
            identidad,
            foto(sesion, cuenta_id),
            pago_id=pago_id,
            fecha_de_transferencia=fecha_de_transferencia,
            motivo=motivo,
            request_id=request_id,
            instante=instante,
        )
    )
    return registrados


def revertir_pago(
    sesion: Session,
    identidad: Identidad,
    *,
    pago_id: UUID,
    creditos: Sequence[UUID],
    ajustes: Sequence[UUID],
    fecha_de_transferencia: date,
    motivo: str,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> list[MovimientoDeReversion]:
    """Revierte, cuenta por cuenta y con las cuentas ya bloqueadas, los movimientos `vigentes` del
    pago (el `pago` o el `reimputacion` crédito de cada parte) y sus `ajustes` de interés. Devuelve
    lo que escribió con su papel en `movimiento_de_pago`."""
    exigir_transaccion(sesion)
    exigir_identidad(sesion, identidad)
    motivo = normalizar_motivo(motivo)
    instante = reloj()
    cuentas = _cuentas_de(sesion, [*creditos, *ajustes])
    bloquear_cuentas(sesion, list(cuentas.values()))  # todas, en orden, antes de escribir
    registrados: list[MovimientoDeReversion] = []
    for cuenta_id in sorted(set(cuentas.values())):
        registrados.extend(
            _revertir_en_la_cuenta(
                sesion,
                identidad,
                cuenta_id,
                [c for c in creditos if cuentas[c] == cuenta_id],
                [a for a in ajustes if cuentas[a] == cuenta_id],
                papel_del_debito="reversion_de_pago",
                pago_id=pago_id,
                fecha_de_transferencia=fecha_de_transferencia,
                motivo=motivo,
                request_id=request_id,
                reloj=reloj,
                instante=instante,
            )
        )
    return registrados


def reimputar_desde(
    sesion: Session,
    identidad: Identidad,
    *,
    pago_id: UUID,
    creditos: Sequence[UUID],
    ajustes: Sequence[UUID],
    desde_unidad_id: UUID,
    cuenta_destino: UUID,
    fecha_de_transferencia: date,
    motivo: str,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> list[MovimientoDeReversion]:
    """El origen de reimputar (H-023, R25): lo que el pago tiene vigente en la cuenta de
    `desde_unidad_id` se deshace como al revertir (el crédito vigente se corrige con un
    `reimputacion` débito, sus ajustes se contra-asientan y P29 cobra el interés de los días ya
    pagados con él), con el candado del origen y del destino tomado juntos y en orden. Devuelve el
    `reimputacion` débito de cada crédito vigente con su importe, que el llamador acredita en el
    destino, y el resto con su papel. Si el pago no tiene nada vigente en esa unidad, `[]`."""
    exigir_transaccion(sesion)
    exigir_identidad(sesion, identidad)
    motivo = normalizar_motivo(motivo)
    instante = reloj()
    cuentas = _cuentas_de(sesion, [*creditos, *ajustes])
    origen = sesion.execute(
        text("SELECT id FROM cuenta WHERE id = ANY(:ids) AND unidad_id = :unidad").bindparams(_IDS),
        {"ids": sorted(set(cuentas.values())), "unidad": desde_unidad_id},
    ).scalar_one_or_none()
    if origen is None:
        return []
    cuenta_origen = UUID(str(origen))
    bloquear_cuentas(sesion, [cuenta_origen, cuenta_destino])
    return _revertir_en_la_cuenta(
        sesion,
        identidad,
        cuenta_origen,
        [c for c in creditos if cuentas[c] == cuenta_origen],
        [a for a in ajustes if cuentas[a] == cuenta_origen],
        papel_del_debito="reimputacion",
        pago_id=pago_id,
        fecha_de_transferencia=fecha_de_transferencia,
        motivo=motivo,
        request_id=request_id,
        reloj=reloj,
        instante=instante,
    )
