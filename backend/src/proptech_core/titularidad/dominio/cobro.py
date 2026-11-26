"""Lo que se le pide a un cobro de la cuenta del vendedor (4d, H-033, D-168.2c): el importe, la
fecha de la transferencia y que no supere lo que se debe. Puro: no lee nada. Los 422 nombran el
campo, nunca el valor (L-007)."""

import re
from datetime import date
from typing import Any

from proptech_core.compartido.dinero import Dinero

#: `[0-9]`, no `\d`: en Python `\d` acepta dígitos de otras escrituras (L-093).
_IMPORTE = re.compile(r"[0-9]+(\.[0-9]{1,2})?")
_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_CERO = Dinero("0.00")


class CobroInvalido(ValueError):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__(campo)


def _importe(valor: Any) -> Dinero:
    if not isinstance(valor, str) or not _IMPORTE.fullmatch(valor):
        raise CobroInvalido("importe")
    importe = Dinero(valor)
    if not importe > _CERO:
        raise CobroInvalido("importe")
    return importe


def _fecha(valor: Any, hoy: date) -> date:
    try:
        if not isinstance(valor, str) or not _FECHA.fullmatch(valor):
            raise ValueError
        fecha = date.fromisoformat(valor)
    except ValueError:
        raise CobroInvalido("fecha") from None
    if fecha > hoy:
        raise CobroInvalido("fecha")
    return fecha


def validar_cobro(*, importe: Any, fecha: Any, hoy: date, deuda: Dinero) -> tuple[Dinero, date]:
    """El importe y la fecha ya leídos. Un cobro mayor que la deuda no se acepta: el vendedor no
    tiene expensas futuras donde aplicar un crédito a favor (D-168)."""
    monto = _importe(importe)
    el_dia = _fecha(fecha, hoy)
    if monto > deuda:
        raise CobroInvalido("importe")
    return monto, el_dia
