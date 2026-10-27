"""5.1: los errores de contexto también se observan en la aserción, no antes."""

from decimal import Decimal, localcontext
from typing import Any

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.reparto import ParteARepartir, repartir


@pytest.mark.parametrize("texto", ["1.00", "-1.00", "999999999999.99"])
def test_rb7_constructor_aislado_del_contexto(texto: str) -> None:
    resultado = None
    error = None
    with localcontext() as contexto:
        contexto.prec = 2
        try:
            resultado = Dinero(texto).a_texto()
        except Exception as fallo:
            error = type(fallo).__name__
    assert (error, resultado) == (None, texto)


def test_qa6_exponente_positivo_sin_float() -> None:
    resultado = None
    error = None
    try:
        resultado = repartir(
            Dinero("100.00"),
            [ParteARepartir("a", Decimal("1E+2"), (0,)), ParteARepartir("b", Decimal("100"), (1,))],
        )
    except Exception as fallo:
        error = type(fallo).__name__
    assert (error, resultado) == (None, {"a": Dinero("50.00"), "b": Dinero("50.00")})


@pytest.mark.parametrize("operacion", ["suma", "resta", "negacion"])
def test_qa7_aritmetica_bajo_contexto_ajeno(operacion: str) -> None:
    a, b = Dinero("999999999999.98"), Dinero("0.01")
    resultado: Any = None
    error = None
    with localcontext() as contexto:
        contexto.prec = 2
        try:
            resultado = {"suma": lambda: a + b, "resta": lambda: a - b, "negacion": lambda: -a}[
                operacion
            ]().a_texto()
        except Exception as fallo:
            error = type(fallo).__name__
    esperado = {
        "suma": "999999999999.99",
        "resta": "999999999999.97",
        "negacion": "-999999999999.98",
    }[operacion]
    assert (error, resultado) == (None, esperado)
