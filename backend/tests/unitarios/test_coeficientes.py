"""R01: texto estricto y aritmética Decimal compartida con la semilla."""

import copy
import random
from decimal import Decimal

import pytest
from pydantic import BaseModel


@pytest.mark.parametrize("texto", ["0.000001", "0.5", "1", "1.000000"])
def test_coeficiente_valido(texto: str) -> None:
    from proptech_core.compartido.coeficientes import Coeficiente

    c = Coeficiente(texto)
    assert c.decimal == Decimal(texto)
    assert c.a_texto() == format(Decimal(texto), ".6f")
    assert Coeficiente(c.a_texto()) == c
    assert hash(Coeficiente(c.a_texto())) == hash(c)
    assert copy.deepcopy(c) == c
    with pytest.raises(AttributeError):
        c._decimal = Decimal("0")


@pytest.mark.parametrize(
    "valor",
    [
        0.5,
        1,
        True,
        None,
        Decimal("0.5"),
        "",
        "0",
        "1.000001",
        "2",
        "0.1234567",
        "-0",
        "+0.5",
        "1e-1",
        "NaN",
        "Infinity",
        "\u0660.\u0665",
        "\uff10.\uff15",
        "0,5",
        *[p + "0.5" for p in [" ", "\t", "\n", "\r", "\x00"]],
        *["0.5" + p for p in [" ", "\t", "\n", "\r", "\x00"]],
    ],
)
def test_coeficiente_rechaza_sin_repetir_valor(valor: object) -> None:
    from proptech_core.compartido.coeficientes import Coeficiente, CoeficienteInvalido

    with pytest.raises(CoeficienteInvalido):
        Coeficiente(valor)  # type: ignore[arg-type]
    with pytest.raises(CoeficienteInvalido) as error:
        Coeficiente("MARCADOR_PRIVADO")
    assert "MARCADOR_PRIVADO" not in str(error.value)


def test_serializacion_y_orden() -> None:
    from proptech_core.compartido.coeficientes import Coeficiente

    class Entrada(BaseModel):
        coeficiente: Coeficiente

    assert Entrada(coeficiente=Coeficiente("0.5")).model_dump(mode="json") == {
        "coeficiente": "0.500000"
    }
    assert Entrada.model_validate({"coeficiente": "0.5"}).coeficiente == Coeficiente("0.5")
    assert Coeficiente("0.4") < Coeficiente("0.5")
    assert Coeficiente("0.5") != 0.5
    with pytest.raises(ValueError):
        Entrada.model_validate({"coeficiente": 0.5})


@pytest.mark.parametrize(
    ("textos", "suma", "diferencia", "estado"),
    [
        (["0.4", "0.6"], "1.000000", "0.000000", "ok"),
        (["0.9999"], "0.999900", "-0.000100", "advertencia"),
        (["1", "0.0001"], "1.000100", "0.000100", "advertencia"),
        (["0.9998"], "0.999800", "-0.000200", "fuera_de_tolerancia"),
        (["1", "0.0002"], "1.000200", "0.000200", "fuera_de_tolerancia"),
        ([], "0.000000", "-1.000000", "fuera_de_tolerancia"),
        (["0.4", "0.4"], "0.800000", "-0.200000", "fuera_de_tolerancia"),
    ],
)
def test_informe(textos: list[str], suma: str, diferencia: str, estado: str) -> None:
    from proptech_core.compartido.coeficientes import Coeficiente, informar_coeficientes

    informe = informar_coeficientes(Coeficiente(t) for t in textos)
    assert informe == {"suma": suma, "diferencia": diferencia, "estado": estado}


def test_propiedad_distancia_a_uno() -> None:
    from proptech_core.compartido.coeficientes import Coeficiente, informar_coeficientes

    generador = random.Random(4101)  # noqa: S311 - propiedades reproducibles
    for _ in range(2000):
        textos = [
            format(Decimal(generador.randint(1, 1000000)) / Decimal("1000000"), "f")
            for _ in range(generador.randrange(20))
        ]
        suma = sum((Decimal(t) for t in textos), Decimal("0"))
        distancia = abs(suma - Decimal("1"))
        estado = (
            "ok"
            if distancia == 0
            else "advertencia"
            if distancia <= Decimal("0.0001")
            else "fuera_de_tolerancia"
        )
        assert informar_coeficientes(map(Coeficiente, textos)) == {
            "suma": format(suma, ".6f"),
            "diferencia": format(suma - Decimal("1"), ".6f"),
            "estado": estado,
        }


def test_informe_no_admite_float() -> None:
    from proptech_core.compartido.coeficientes import informar_coeficientes

    with pytest.raises(TypeError):
        informar_coeficientes([0.5])  # type: ignore[list-item]
