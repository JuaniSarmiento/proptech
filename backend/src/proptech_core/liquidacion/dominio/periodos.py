"""El orden de los períodos (R40, D-157): no se liquida con el período anterior sin emitir."""

from collections.abc import Collection
from datetime import date

PERIODO_EMITIDO = "periodo_emitido"
PERIODO_ANTERIOR_SIN_EMITIR = "periodo_anterior_sin_emitir"


def _mes_anterior(periodo: date) -> date:
    return (
        date(periodo.year - 1, 12, 1)
        if periodo.month == 1
        else date(periodo.year, periodo.month - 1, 1)
    )


def motivo_de_rechazo(periodo: date, emitidos: Collection[date]) -> str | None:
    """`emitidos` son los períodos del edificio con una emisión sin anular (una anulada no
    cuenta). Un período emitido se rechaza; sin emisiones, cualquier período es el primero; con
    emisiones, sólo el que sigue a uno emitido. `None` si se puede preliquidar."""
    if periodo in emitidos:
        return PERIODO_EMITIDO
    if emitidos and _mes_anterior(periodo) not in emitidos:
        return PERIODO_ANTERIOR_SIN_EMITIR
    return None
