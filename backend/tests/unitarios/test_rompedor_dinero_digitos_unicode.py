"""Regresion (rompedor, cambio 1b vuelta 2): `Dinero` se construye "solo desde
texto con el formato `-?digitos(.digitos)?`" (D5, specs/representacion-de-montos).
El patron usaba `\\d` sin `re.ASCII`, y en Python `\\d` sin ese flag matchea
cualquier digito Unicode de categoria Nd (arabigo-indico, arabigo-indico
extendido, ancho completo, etc.), no solo 0-9. `Decimal()` ademas los
interpretaba con su valor numerico: un texto compuesto solo por digitos
arabigo-indicos (equivalente a "123.00") quedaba aceptado como monto valido,
indistinguible a simple vista del propio `a_texto()` que produce el tipo.
Arreglado agregando `re.ASCII` al patron (`dinero.py`); estos tests quedan
como regresion para que no vuelva a pasar.
"""

from __future__ import annotations

import pytest

# Digitos arabigo-indicos (U+0660..0669), arabigo-indicos extendidos/persas
# (U+06F0..06F9) y de ancho completo (U+FF10..FF19): todos categoria Unicode
# Nd, todos matcheados por `\d` sin `re.ASCII`. Construidos con \u para que
# el archivo fuente no lleve los glifos no-ASCII en texto plano.
_NO_ASCII = [
    "١٢٣.٠٠",  # noqa: RUF001 - equivalente a "123.00", arabigo-indico
    "１２３.００",  # noqa: RUF001 - equivalente a "123.00", ancho completo
    "۱۲۳",  # equivalente a "123", arabigo-indico extendido (persa)
]


@pytest.mark.parametrize("texto", _NO_ASCII)
def test_dinero_rechaza_digitos_no_ascii(texto: str) -> None:
    """La spec exige el formato `-?digitos(.digitos)?`: digitos quiere decir
    0-9, no cualquier digito Unicode."""
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero(texto)


def test_dinero_con_digitos_no_ascii_nunca_llega_a_existir_para_compararse() -> None:
    """Antes del fix, un texto no-ASCII (equivalente numericamente a "123.00")
    no se rechazaba y terminaba siendo el mismo objeto `Dinero` que su
    equivalente ASCII: la unica forma de representar un monto que exige la
    spec (D-046, R07) dejaba de ser unica. El fix lo cierra en el origen: ese
    texto nunca llega a construir un `Dinero` con el que comparar."""
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    texto_no_ascii = "١٢٣.٠٠"  # noqa: RUF001 - equivalente a "123.00"
    with pytest.raises(MontoInvalido):
        Dinero(texto_no_ascii)
