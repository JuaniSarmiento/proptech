"""Regla Unicode compartida de texto visible y representable (R3B-1/7)."""

from collections.abc import Callable

import pytest

from proptech_core.compartido.texto import recortado_sin_control, sin_caracteres_de_control


@pytest.mark.parametrize(
    "caracter",
    [
        "\x00",
        "\x1f",
        "\x7f",
        "\x85",
        "\u200b",
        "\u2060",
        "\ufeff",
        "\u00ad",
        "\u202e",
        "\ud800",
        "\udfff",
        "\ue000",
        "\u0378",
        "\u2028",
        "\u2029",
        "\u034f",
        "\u115f",
        "\u3164",
        "\u17b4",
        "\u180b",
        "\ufe0f",
        "\uffa0",
        "\U000e0100",
    ],
)
@pytest.mark.parametrize("validar", [recortado_sin_control, sin_caracteres_de_control])
def test_texto_no_representable_o_invisible_se_rechaza_sin_repetirlo(
    caracter: str, validar: Callable[[str], str]
) -> None:
    valor = "MARCADOR" + caracter
    with pytest.raises(ValueError) as error:
        validar(valor)
    assert "MARCADOR" not in str(error.value)
    assert caracter not in str(error.value)


@pytest.mark.parametrize("valor", ["José", "Jose\u0301", "中文", "🏠", "1 A"])
def test_texto_visible_se_conserva(valor: str) -> None:
    assert sin_caracteres_de_control(valor) == valor
    assert recortado_sin_control(" " + valor + " ") == valor
