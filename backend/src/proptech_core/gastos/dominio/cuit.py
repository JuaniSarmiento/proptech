"""Validación de CUIT (R12, D-019): la llave con la que se identifica al
proveedor emisor de una factura.

`fullmatch` y `re.ASCII` (L-008): un CUIT con dígitos de otro alfabeto, con
espacios o con un salto de línea al borde no pasa, aunque `Decimal` o un
`int()` los normalizarían sin avisar. `FORMATO_CUIT` es la única fuente del
texto que describe el formato esperado: el validador y el mensaje de error
(L-051) la comparten, nunca un mensaje genérico aparte.
"""

from __future__ import annotations

import re

FORMATO_CUIT = "once dígitos (0-9 ASCII), sin espacios ni guiones, con dígito verificador válido"

_PATRON_CUIT = re.compile(r"[0-9]{11}", re.ASCII)
_PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def cuit_valido(valor: str) -> bool:
    """Once dígitos ASCII con coincidencia completa y dígito verificador
    correcto (módulo 11). Un resto que daría dígito verificador 10 no tiene
    CUIT válido posible con ese prefijo: se rechaza, no se trunca."""
    if not isinstance(valor, str) or _PATRON_CUIT.fullmatch(valor) is None:
        return False
    digitos = [int(c) for c in valor]
    suma = sum(d * p for d, p in zip(digitos[:10], _PESOS, strict=True))
    verificador = 11 - (suma % 11)
    if verificador == 11:
        verificador = 0
    if verificador == 10:
        return False
    return digitos[10] == verificador
