"""Lo que el vecino ve de su unidad (change 11, H-038, D-170): las cifras del libro a una fecha.

Es una lectura: no escribe nada ni recalcula plata. Toma una sola foto de la cuenta (D12) y de ella
saca el total a pagar, el vencimiento, el saldo anterior y los créditos; el interés vencido sale de
la situación de cobranza. Para el inquilino (D-170.2) la deuda y el vencimiento dejan afuera el
componente `extraordinaria`.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.aplicacion.cobranza import situacion_de_cuenta
from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto
from proptech_core.cuenta_corriente.aplicacion.lecturas import cuenta_de_unidad, foto

_CERO = Dinero("0.00")
_EXTRAORDINARIA = "extraordinaria"


@dataclass(frozen=True)
class CifrasDeUnidad:
    total_a_pagar: Dinero = _CERO
    vencimiento: date | None = None
    deuda_anterior: Dinero = _CERO
    intereses: Dinero = _CERO
    credito_aplicable: Dinero = _CERO
    credito_retenido: Dinero = _CERO


def cifras_de_unidad(
    sesion: Session,
    *,
    unidad_id: UUID,
    fecha: date,
    emision_id: UUID | None,
    sin_extraordinaria: bool,
) -> CifrasDeUnidad:
    """Las cifras de la unidad a `fecha`. `emision_id` es la emisión más reciente no anulada del
    edificio (el saldo anterior es la deuda sin ella; `None`, sin emisión, es cero). Una unidad sin
    cuenta (nada emitido ni cargado) da todo en cero y sin vencimiento."""
    cuenta_id = cuenta_de_unidad(sesion, unidad_id=unidad_id)
    if cuenta_id is None:
        return CifrasDeUnidad()
    estado = foto(sesion, cuenta_id).estado
    pendientes = {
        clave: residual
        for clave, residual in estado.residual.items()
        if residual > _CERO and not (sin_extraordinaria and clave[1].value == _EXTRAORDINARIA)
    }
    total = sumar(pendientes.values()) if sin_extraordinaria else estado.deuda
    con_deuda = {obligacion for obligacion, _ in pendientes}
    vencimientos = [
        o.vencimiento
        for o in estado.obligaciones
        if o.id in estado.obligaciones_que_cuentan and o.id in con_deuda
    ]
    try:
        intereses = situacion_de_cuenta(sesion, cuenta_id=cuenta_id, fecha=fecha).interes_vencido
    except (
        Conflicto
    ):  # el edificio sin configuración vigente a esa fecha no tiene interés que mostrar
        intereses = _CERO
    return CifrasDeUnidad(
        total_a_pagar=total,
        vencimiento=min(vencimientos) if vencimientos else None,
        deuda_anterior=_CERO if emision_id is None else estado.deuda_sin_emision(emision_id),
        intereses=intereses,
        credito_aplicable=estado.credito_a_favor_aplicable,
        credito_retenido=estado.credito_a_favor_retenido,
    )


def importe_imputado_sin_extraordinaria(
    sesion: Session, *, unidad_id: UUID, movimiento_ids: frozenset[UUID]
) -> Dinero:
    """Lo que de esos movimientos (los `pago` de un pago informado) quedó imputado a interés,
    ordinaria y fondo de reserva en la cuenta de la unidad: lo que ve el inquilino (D-170.2)."""
    cuenta_id = cuenta_de_unidad(sesion, unidad_id=unidad_id)
    if cuenta_id is None:
        return _CERO
    estado = foto(sesion, cuenta_id).estado
    return sumar(
        i.importe
        for i in estado.imputaciones_que_cuentan
        if i.movimiento_id in movimiento_ids and i.componente.value != _EXTRAORDINARIA
    )
