"""Lo que el libro sabía de una cuenta a una fecha de corte, sin base (10b, H-041, R21, D-171).

Es una lectura: el estado de la cuenta se recalcula con las mismas reglas de siempre
(`calcular_estado`) sobre lo que ya existía a la fecha de corte. Cuentan los movimientos con
`fecha_valor` hasta el corte (un pago confirmado hoy con transferencia anterior cuenta, D-166) y,
de las obligaciones, las que vencen hasta el corte para el saldo y las que vencen después, aparte.
Nada de lo que no está en el libro entra: ni cargos sin liquidar ni gastos del período en curso.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.dominio.estado import (
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class CuotaPosterior:
    """Una obligación no anulada que vence después del corte y lo que le queda pendiente a esa
    fecha."""

    periodo: date
    vencimiento: date
    importe: Dinero


@dataclass(frozen=True)
class DeudaALaFecha:
    capital: Dinero
    intereses: Dinero
    cuotas_posteriores: tuple[CuotaPosterior, ...]

    @property
    def saldo(self) -> Dinero:
        return self.capital + self.intereses


def deuda_a_la_fecha(
    obligaciones: Iterable[Obligacion],
    movimientos: Iterable[Movimiento],
    imputaciones: Iterable[ImputacionRegistrada],
    emisiones_anuladas: Iterable[UUID],
    corte: date,
) -> DeudaALaFecha:
    todas = tuple(obligaciones)
    estado = calcular_estado(
        todas,
        [m for m in movimientos if m.fecha_valor <= corte],
        imputaciones,
        emisiones_anuladas,
    )

    def pendiente(obligacion: Obligacion, *, interes: bool | None) -> Dinero:
        return sumar(
            residual
            for (oid, componente), residual in estado.residual.items()
            if oid == obligacion.id
            and (interes is None or (componente is Componente.INTERES) == interes)
        )

    vencidas = [
        o for o in todas if o.id in estado.obligaciones_que_cuentan and o.vencimiento <= corte
    ]
    posteriores = sorted(
        (o for o in todas if o.id in estado.obligaciones_que_cuentan and o.vencimiento > corte),
        key=lambda o: (o.periodo, o.vencimiento, str(o.id)),
    )
    return DeudaALaFecha(
        capital=sumar(pendiente(o, interes=False) for o in vencidas),
        intereses=sumar(pendiente(o, interes=True) for o in vencidas),
        cuotas_posteriores=tuple(
            CuotaPosterior(o.periodo, o.vencimiento, pendiente(o, interes=None))
            for o in posteriores
        ),
    )
