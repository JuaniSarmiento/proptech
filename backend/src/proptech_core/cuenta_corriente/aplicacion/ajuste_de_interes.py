"""El ajuste del interés cobrado de más a un pago confirmado tarde (change 8, H-021, E7, D-166).

Una emisión con período posterior a la fecha de la transferencia le cobró interés al vecino por
días en que ya había pagado. Antes de registrar el pago, cada uno de esos intereses se recalcula
sobre sus mismos tramos (con la tasa y la forma guardadas en `tramo_de_interes`, nunca la
configuración de hoy) con la base que habría tenido con el pago imputado a la fecha de la
transferencia; la diferencia es un `ajuste_de_interes` con destino ese interés. La cuenta queda
como la de quien confirmó a tiempo.

Lo que no entra en el interés (otro crédito ya lo pagó) se registra hasta lo que entra y el resto
se devuelve: la confirmación no lo registra sola (E7), para que el administrador lo corrija con R08.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    Reloj,
    ahora_utc,
    imputar_pendientes,
    registrar_credito,
)
from proptech_core.cuenta_corriente.aplicacion.errores import exigir_transaccion
from proptech_core.cuenta_corriente.aplicacion.lecturas import FotoDeCuenta, foto
from proptech_core.cuenta_corriente.aplicacion.pagos import (
    emisiones_posteriores,
    imputaciones_del_pago,
)
from proptech_core.cuenta_corriente.dominio.estado import (
    ImputacionRegistrada,
    Movimiento,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Destino
from proptech_core.cuenta_corriente.dominio.intereses import (
    FormaDeCalculo,
    TramoGuardado,
    base_de_capital,
    diferencia_de_interes,
)

_CERO = Dinero("0.00")
#: Fijo: de él sale el `operacion_id` de cada ajuste (confirmar dos veces es una repetición).
_ESPACIO_DE_AJUSTES = UUID("b3e8f1a4-6c2d-4f7a-9d15-2a8c4e6b0f93")
_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))


@dataclass(frozen=True)
class AjusteDeInteres:
    movimiento_id: UUID
    interes_id: UUID
    obligacion_id: UUID
    importe: Dinero


@dataclass(frozen=True)
class ResultadoDelAjuste:
    registrados: tuple[AjusteDeInteres, ...]
    #: Lo que correspondía ajustar y no entró en el interés: se devuelve, no se registra.
    sin_destino: Dinero


def _sumar(montos: Iterable[Dinero]) -> Dinero:
    total = _CERO
    for monto in montos:
        total = total + monto
    return total


def _forma(valor: str) -> FormaDeCalculo:
    return "mes_entero" if valor == "mes_entero" else "proporcional_por_dia"


def _tramos_guardados(
    sesion: Session, cuenta_id: UUID, interes_ids: Sequence[UUID]
) -> dict[UUID, tuple[list[TramoGuardado], int]]:
    """Los tramos de cada interés con su tasa y su forma, y los días de gracia con que se cobró."""
    filas = sesion.execute(
        text(
            "SELECT movimiento_id, desde, hasta, tasa_mensual::text AS tasa, forma_de_calculo, "
            "dias_de_gracia FROM tramo_de_interes WHERE cuenta_id = :cuenta "
            "AND movimiento_id = ANY(:ids) ORDER BY desde"
        ).bindparams(_IDS),
        {"cuenta": cuenta_id, "ids": list(interes_ids)},
    ).all()
    por_interes: dict[UUID, tuple[list[TramoGuardado], int]] = {}
    for f in filas:
        tramos, _ = por_interes.setdefault(UUID(str(f.movimiento_id)), ([], int(f.dias_de_gracia)))
        tramos.append(
            TramoGuardado(f.desde, f.hasta, Porcentaje(f.tasa), _forma(f.forma_de_calculo))
        )
    return por_interes


def diferencias_por_el_pago(
    sesion: Session, actual: FotoDeCuenta, importe: Dinero, fecha_valor: date
) -> list[tuple[Movimiento, Dinero]]:
    """Por cada interés que cuenta y que es de una emisión posterior a la fecha, cuánto menos habría
    cobrado con el pago imputado a esa fecha (E6). Sólo las diferencias positivas. No escribe."""
    posteriores = emisiones_posteriores(sesion, actual, fecha_valor)
    intereses = sorted(
        (
            m
            for m in actual.movimientos.values()
            if m.tipo == "interes"
            and m.id in actual.estado.movimientos_que_cuentan
            and m.emision_id in posteriores
            and m.obligacion_id is not None
        ),
        key=lambda m: (m.fecha_valor, str(m.id)),
    )
    if not intereses:
        return []
    tramos = _tramos_guardados(sesion, actual.cuenta_id, [m.id for m in intereses])
    # El pago como quedaría en el libro: su crédito y sus imputaciones, después de las que ya hay.
    imputaciones = imputaciones_del_pago(sesion, actual, fecha_valor, importe)
    pago = Movimiento(uuid4(), "pago", "credito", importe, fecha_valor, datetime.now(UTC))
    orden = max((i.orden for i in actual.imputaciones), default=0)
    del_pago = [
        ImputacionRegistrada(pago.id, i.obligacion_id, i.componente, i.importe, orden + n + 1)
        for n, i in enumerate(imputaciones)
    ]
    movimientos_despues = {**actual.movimientos, pago.id: pago}
    estado_despues = calcular_estado(
        actual.estado.obligaciones,
        movimientos_despues.values(),
        [*actual.imputaciones, *del_pago],
        actual.anuladas,
    )
    por_id = {o.id: o for o in actual.estado.obligaciones}
    resultado: list[tuple[Movimiento, Dinero]] = []
    for interes in intereses:
        if interes.obligacion_id is None or interes.id not in tramos:
            continue
        guardados, gracia = tramos[interes.id]
        obligacion = por_id[interes.obligacion_id]
        diferencia = diferencia_de_interes(
            guardados,
            base_de_capital(obligacion, actual.estado, actual.movimientos, gracia),
            base_de_capital(obligacion, estado_despues, movimientos_despues, gracia),
        )
        if diferencia > _CERO:
            resultado.append((interes, diferencia))
    return resultado


def ajustar_el_interes(
    sesion: Session,
    identidad: Identidad,
    *,
    cuenta_id: UUID,
    importe: Dinero,
    fecha_valor: date,
    operacion_base: UUID,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> ResultadoDelAjuste:
    """Registra, antes del pago y con la cuenta ya bloqueada, un `ajuste_de_interes` por cada
    interés cobrado de más. `operacion_base` identifica la parte del pago: de ella sale el
    `operacion_id` de cada ajuste, así que repetir la confirmación no registra otro."""
    exigir_transaccion(sesion)
    imputar_pendientes(sesion, cuenta_id, uuid4(), reloj())
    actual = foto(sesion, cuenta_id)
    entran: dict[UUID, Dinero] = {}
    registrados: list[AjusteDeInteres] = []
    sin_destino = _CERO
    for interes, diferencia in diferencias_por_el_pago(sesion, actual, importe, fecha_valor):
        obligacion_id = interes.obligacion_id
        if obligacion_id is None:
            continue
        ya_ajustado = _sumar(
            m.importe
            for m in actual.movimientos.values()
            if m.tipo == "ajuste_de_interes"
            and m.enlazado_a == interes.id
            and m.id in actual.estado.movimientos_que_cuentan
        )
        tope_del_interes = interes.importe - ya_ajustado
        a_ajustar = diferencia if diferencia < tope_del_interes else tope_del_interes
        if not a_ajustar > _CERO:
            continue
        residual = actual.estado.residual.get((obligacion_id, Componente.INTERES), _CERO)
        libre = residual - entran.get(obligacion_id, _CERO)
        entra = _CERO if not libre > _CERO else (a_ajustar if a_ajustar < libre else libre)
        if entra > _CERO:
            movimiento_id = registrar_credito(
                sesion,
                identidad,
                cuenta_id=cuenta_id,
                tipo="ajuste_de_interes",
                importe=entra,
                fecha_valor=interes.fecha_valor,
                operacion_id=uuid5(_ESPACIO_DE_AJUSTES, f"{operacion_base}|{interes.id}"),
                destino=Destino(obligacion_id, Componente.INTERES),
                request_id=request_id,
                reloj=reloj,
                enlazado_a=interes.id,
            )
            entran[obligacion_id] = entran.get(obligacion_id, _CERO) + entra
            registrados.append(AjusteDeInteres(movimiento_id, interes.id, obligacion_id, entra))
        sin_destino = sin_destino + (a_ajustar - entra)
    return ResultadoDelAjuste(tuple(registrados), sin_destino)
