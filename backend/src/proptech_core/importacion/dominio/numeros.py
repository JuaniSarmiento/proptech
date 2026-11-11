"""Lectura de números del Excel, exacta y sin `float` (design D2, E14).

Un texto acepta coma decimal, con o sin punto de miles (`0,083333`, `1.234,56`), o punto decimal sin
coma (`45.50`). Un texto ambiguo (`1.234`: un solo punto y tres dígitos después, que puede ser mil
doscientos treinta y cuatro) se rechaza, igual que el que tiene más decimales de los permitidos:
nunca se redondea. Una celda numérica ya llega en notación fija y exacta (`numerico=True`): ahí
`0.125` es una fracción, no un texto ambiguo.
"""

from __future__ import annotations

import re
from decimal import Decimal

_CON_COMA = re.compile(
    r"(?P<signo>[+-]?)(?P<entera>\d+|\d{1,3}(?:\.\d{3})+),(?P<fraccion>\d+)", re.ASCII
)
_CON_PUNTO = re.compile(r"(?P<signo>[+-]?)(?P<entera>\d+)(?:\.(?P<fraccion>\d+))?", re.ASCII)
_AMBIGUO = re.compile(r"\d{1,3}\.\d{3}", re.ASCII)


class NumeroInvalido(ValueError):
    """El texto no es un número aceptable; el mensaje es el motivo y no repite el texto."""


def leer_decimal(texto: str, *, decimales: int, numerico: bool = False) -> Decimal:
    limpio = texto.strip()
    if "," in limpio:
        coincidencia = _CON_COMA.fullmatch(limpio)
        if coincidencia is None:
            raise NumeroInvalido("no es un número: usá coma decimal (0,5) o punto decimal (0.5)")
        entera = coincidencia["entera"].replace(".", "")
    else:
        coincidencia = _CON_PUNTO.fullmatch(limpio)
        if coincidencia is None:
            raise NumeroInvalido("no es un número: usá coma decimal (0,5) o punto decimal (0.5)")
        entera = coincidencia["entera"]
        if not numerico and _AMBIGUO.fullmatch(limpio.lstrip("+-")):
            raise NumeroInvalido(
                "es ambiguo (puede ser un decimal o un número con punto de miles): "
                "escribilo con coma decimal"
            )
    fraccion = coincidencia["fraccion"] or ""
    if len(fraccion) > decimales:
        raise NumeroInvalido(f"tiene más de {decimales} decimales y no se redondea")
    return Decimal(f"{coincidencia['signo']}{entera}" + (f".{fraccion}" if fraccion else ""))
