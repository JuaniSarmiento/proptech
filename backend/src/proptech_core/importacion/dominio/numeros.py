"""PROVISORIO (rojo de la tarea 1.3): la lectura real de números viene en el commit siguiente."""

from __future__ import annotations

from decimal import Decimal


class NumeroInvalido(ValueError):
    """El texto no es un número aceptable; el mensaje es el motivo, sin repetir el texto."""


def leer_decimal(texto: str, *, decimales: int, numerico: bool = False) -> Decimal:
    return Decimal(0)
