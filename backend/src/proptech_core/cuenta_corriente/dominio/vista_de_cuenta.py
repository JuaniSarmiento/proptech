"""Cómo se ve una cuenta de persona (4d, H-033): lo que se le trasladó por período y componente, y
sus movimientos en el orden del libro. Puro: lo calcula del estado, no lee nada."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.estado import EstadoDeCuenta, Movimiento
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

_CERO = Dinero("0.00")
_ORDEN = list(Componente)


@dataclass(frozen=True)
class TotalesDeComponente:
    debe: Dinero
    cobrado: Dinero
    pendiente: Dinero


@dataclass(frozen=True)
class PeriodoDeCuenta:
    periodo: date
    #: En el orden de R04 (interés, ordinaria, fondo de reserva, extraordinaria).
    componentes: dict[Componente, TotalesDeComponente]


def periodos_de(estado: EstadoDeCuenta) -> list[PeriodoDeCuenta]:
    """Por período (ascendente) y componente: lo debido, lo imputado por los cobros y lo pendiente
    (el residual del libro). Sólo los componentes que tuvieron algo que deber: varias obligaciones
    del mismo período (dos cambios de titular) se juntan."""
    periodo_de = {o.id: o.periodo for o in estado.obligaciones}
    juntos: dict[tuple[date, Componente], list[Dinero]] = {}
    for (obligacion, componente), debe in estado.debido.items():
        if not debe > _CERO:
            continue
        acumulado = juntos.setdefault((periodo_de[obligacion], componente), [_CERO, _CERO, _CERO])
        acumulado[0] = acumulado[0] + debe
        acumulado[1] = acumulado[1] + estado.imputado[(obligacion, componente)]
        acumulado[2] = acumulado[2] + estado.residual[(obligacion, componente)]
    periodos: dict[date, dict[Componente, TotalesDeComponente]] = {}
    for (periodo, componente), (debe, cobrado, pendiente) in sorted(
        juntos.items(), key=lambda par: (par[0][0], _ORDEN.index(par[0][1]))
    ):
        periodos.setdefault(periodo, {})[componente] = TotalesDeComponente(debe, cobrado, pendiente)
    return [PeriodoDeCuenta(p, c) for p, c in periodos.items()]


def movimientos_en_orden(movimientos: Iterable[Movimiento]) -> list[Movimiento]:
    """El orden del libro: `registrado_en` y, a igual instante, el `id`."""
    return sorted(movimientos, key=lambda m: (m.registrado_en, str(m.id)))
