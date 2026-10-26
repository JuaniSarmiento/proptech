"""R07: redondeo suelto y reparto son operaciones distintas."""

from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from proptech_core.compartido.dinero import Dinero, MontoInvalido, sumar
from proptech_core.compartido.reparto import (
    ParteARepartir,
    RepartoInvalido,
    redondear_al_centavo,
    repartir,
)


@pytest.mark.parametrize(
    "entrada,salida",
    [
        ("0.125", "0.13"),
        ("0.124999", "0.12"),
        ("-0.125", "-0.13"),
        ("999999999999.994", "999999999999.99"),
    ],
)
def test_redondeo(entrada: str, salida: str) -> None:
    esperado = Dinero(salida)
    with localcontext() as contexto:
        contexto.prec = 10
        contexto.rounding = ROUND_DOWN
        assert redondear_al_centavo(Decimal(entrada)) == esperado


@pytest.mark.parametrize(
    "entrada",
    [0.125, Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), Decimal("999999999999.995")],
)
def test_redondeo_invalido(entrada: object) -> None:
    with pytest.raises(MontoInvalido):
        redondear_al_centavo(entrada)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        (["L-PB", "1A", "C1", "B1", "10A"], ["1A", "10A", "B1", "C1", "L-PB"]),
        (["PB", "1", "1A", "A1"], ["1", "1A", "A1", "PB"]),
        (["10", "2", "1"], ["1", "2", "10"]),
        (["10A", "2B"], ["2B", "10A"]),
        (["a2", "A2"], ["A2", "a2"]),
        (["\u0661\u0660", "10"], ["10", "\u0661\u0660"]),
    ],
)
def test_orden_natural(entrada: list[str], esperado: list[str]) -> None:
    from uuid import UUID

    from proptech_core.compartido.reparto import clave_de_orden_natural

    assert sorted(entrada, key=lambda x: clave_de_orden_natural(x, UUID(int=1))) == esperado


def test_orden_natural_desempata_por_uuid() -> None:
    from uuid import UUID

    from proptech_core.compartido.reparto import clave_de_orden_natural

    assert clave_de_orden_natural("1", UUID(int=1)) < clave_de_orden_natural("1", UUID(int=2))


def partes_de(pesos: list[str]) -> list[ParteARepartir]:
    return [ParteARepartir(str(i), Decimal(p), (i,)) for i, p in enumerate(pesos)]


@pytest.mark.parametrize(
    "total,pesos,esperado",
    [
        ("1000000", ["1"] * 150, ["6666.67"] * 100 + ["6666.66"] * 50),
        ("1234.56", ["1"], ["1234.56"]),
        ("100", ["0.4999", "0.5"], ["49.99", "50.01"]),
        ("0", ["1"] * 3, ["0.00"] * 3),
        ("2", ["1"] * 3, ["0.67", "0.67", "0.66"]),
        ("100", ["0.333333", "0.333333", "0.333334"], ["33.33", "33.33", "33.34"]),
        ("0.05", ["0.6", "0.25", "0.15"], ["0.03", "0.01", "0.01"]),
        ("-2", ["1"] * 3, ["-0.67", "-0.67", "-0.66"]),
        ("0.01", ["1"] * 150, ["0.01"] + ["0.00"] * 149),
        ("1", ["0", "1"], ["0.00", "1.00"]),
        ("1", ["1E+2", "100"], ["0.50", "0.50"]),
    ],
)
def test_ejemplos_reparto(total: str, pesos: list[str], esperado: list[str]) -> None:
    resultado = repartir(Dinero(total), partes_de(pesos))
    assert sumar(resultado.values()) == Dinero(total)
    assert [resultado[str(i)].a_texto() for i in range(len(pesos))] == esperado


def test_reparto_natural_y_cien_permutaciones() -> None:
    import random
    from uuid import UUID

    from proptech_core.compartido.reparto import clave_de_orden_natural

    partes = [
        ParteARepartir(k, Decimal("1"), clave_de_orden_natural(k, UUID(int=i)))
        for i, k in enumerate(["1", "2", "10"])
    ]
    esperado = {"1": Dinero("0.67"), "2": Dinero("0.67"), "10": Dinero("0.66")}
    aleatorio = random.Random(42)  # noqa: S311 (permutaciones reproducibles, sin seguridad)
    for _ in range(100):
        aleatorio.shuffle(partes)
        assert repartir(Dinero("2"), partes) == esperado
    assert sumar(redondear_al_centavo(Decimal("2") / 3) for _ in range(3)) == Dinero("2.01")


@pytest.mark.parametrize(
    "peso",
    [
        Decimal("-0.1"),
        0.1,
        1,
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("0.0000001"),
        Decimal("1000000000000"),
        Decimal("1E-999999"),
    ],
)
def test_peso_invalido(peso: object) -> None:
    with pytest.raises(RepartoInvalido):
        repartir(Dinero("1"), [ParteARepartir("a", peso, (0,))])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "total,partes",
    [
        (1.0, partes_de(["1"])),
        (Dinero("1"), []),
        (Dinero("1"), partes_de(["0", "0"])),
        (Dinero("1"), [ParteARepartir("x", Decimal("1"), (0,))] * 2),
    ],
)
def test_reparto_invalido(total: object, partes: list[ParteARepartir]) -> None:
    with pytest.raises(RepartoInvalido):
        repartir(total, partes)  # type: ignore[arg-type]
