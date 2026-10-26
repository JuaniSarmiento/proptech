"""Aritmética exacta, aislada del contexto de quien llama (D5)."""

from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from proptech_core.compartido.dinero import Dinero, MontoInvalido, sumar


@pytest.mark.parametrize(
    "a,b,suma,resta",
    [
        ("0.10", "0.20", "0.30", "-0.10"),
        ("999999999999.98", "0.01", "999999999999.99", "999999999999.97"),
        ("-1.00", "1.00", "0.00", "-2.00"),
    ],
)
def test_suma_y_resta(a: str, b: str, suma: str, resta: str) -> None:
    x = Dinero(a)
    y = Dinero(b)
    with localcontext() as ctx:
        ctx.prec = 10
        ctx.rounding = ROUND_DOWN
        assert (x + y).a_texto() == suma
        assert (x - y).a_texto() == resta


@pytest.mark.parametrize(
    "texto,esperado",
    [("12.50", "-12.50"), ("0.00", "0.00"), ("-999999999999.99", "999999999999.99")],
)
def test_negacion(texto: str, esperado: str) -> None:
    assert (-Dinero(texto)).a_texto() == esperado


def test_sumar_iterable() -> None:
    assert sumar([]) == Dinero("0.00")
    assert sumar(iter([Dinero("0.10"), Dinero("0.20")])) == Dinero("0.30")


@pytest.mark.parametrize("otro", [1, 0.5, Decimal("0.5"), "0.5"])
def test_otro_operando(otro: object) -> None:
    with pytest.raises(TypeError):
        Dinero("1") + otro
    with pytest.raises(TypeError):
        Dinero("1") - otro


@pytest.mark.parametrize("a,b", [("999999999999.99", "0.01"), ("-999999999999.99", "-0.01")])
def test_desborde(a: str, b: str) -> None:
    with pytest.raises(MontoInvalido):
        Dinero(a) + Dinero(b)
