"""La deuda de una unidad a una fecha de corte, desde el libro (10b, H-041, R21, D-171).

Es una lectura: sin candados ni escrituras. El saldo, el capital, los intereses registrados y las
cuotas que vencen después salen del estado de la cuenta recalculado a la fecha de corte
(`dominio/a_la_fecha.py`). El interés corrido de R21 (D-081) es el cálculo de la emisión
(`calcular_intereses_del_corte`, R03) para un corte en esa fecha sobre el libro tal como está:
nunca se registra ni se suma al saldo.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.aplicacion.emisiones import calcular_intereses_del_corte
from proptech_core.cuenta_corriente.aplicacion.lecturas import cuenta_de_unidad, foto
from proptech_core.cuenta_corriente.dominio.a_la_fecha import CuotaPosterior, deuda_a_la_fecha

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class DeudaDeLaUnidad:
    capital: Dinero
    intereses: Dinero
    interes_corrido: Dinero
    cuotas_posteriores: tuple[CuotaPosterior, ...]

    @property
    def saldo(self) -> Dinero:
        return self.capital + self.intereses


def deuda_de_la_unidad_a_la_fecha(
    sesion: Session, *, complejo_id: UUID, unidad_id: UUID, corte: date
) -> DeudaDeLaUnidad:
    """Una unidad sin cuenta (todavía no se emitió nada) no debe nada. `Conflicto("configuracion")`
    si hay vencimientos y ninguna versión de configuración rige al corte (el interés no se puede
    calcular)."""
    cuenta = cuenta_de_unidad(sesion, unidad_id=unidad_id)
    if cuenta is None:
        return DeudaDeLaUnidad(_CERO, _CERO, _CERO, ())
    actual = foto(sesion, cuenta)
    a_la_fecha = deuda_a_la_fecha(
        actual.estado.obligaciones,
        actual.movimientos.values(),
        actual.imputaciones,
        actual.anuladas,
        corte,
    )
    _, calculados = calcular_intereses_del_corte(sesion, complejo_id, corte, {cuenta: actual})
    corrido = sumar(i.importe for i in calculados.get(cuenta, []))
    return DeudaDeLaUnidad(
        a_la_fecha.capital, a_la_fecha.intereses, corrido, a_la_fecha.cuotas_posteriores
    )
