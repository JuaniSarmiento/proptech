"""2.1: validador puro de CUIT (R12). `fullmatch` + `re.ASCII` (L-008)."""

import pytest

from proptech_core.gastos.dominio.cuit import cuit_valido

#: Dígito verificador correcto, calculado a mano (módulo 11, pesos
#: 5,4,3,2,7,6,5,4,3,2) y verificado contra un CUIT real documentado
#: (20-32964299-3).
_VALIDOS = ["20123456786", "20329642993", "30712345604", "27123456713"]


@pytest.mark.parametrize("cuit", _VALIDOS)
def test_cuit_valido_pasa(cuit: str) -> None:
    assert cuit_valido(cuit) is True


@pytest.mark.parametrize(
    "cuit",
    [
        "20123456780",  # mismo prefijo, dígito verificador equivocado (era 6)
        "20329642990",  # idem, era 3
    ],
)
def test_digito_verificador_incorrecto_falla(cuit: str) -> None:
    assert cuit_valido(cuit) is False


@pytest.mark.parametrize(
    "cuit",
    [
        "2012345678",  # diez dígitos
        "201234567860",  # doce dígitos
        "",
    ],
)
def test_largo_distinto_falla(cuit: str) -> None:
    assert cuit_valido(cuit) is False


@pytest.mark.parametrize(
    "cuit",
    [
        "٢٠١٢٣٤٥٦٧٨٦",  # dígitos arábigo-índicos, mismo valor numérico que el válido
        "20123456786 ",  # espacio al final
        " 20123456786",  # espacio al principio
        "20123456786\n",  # salto de línea final
        "\n20123456786",
    ],
)
def test_no_ascii_o_espacios_al_borde_falla(cuit: str) -> None:
    assert cuit_valido(cuit) is False
