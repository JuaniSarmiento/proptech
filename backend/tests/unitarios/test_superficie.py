"""Tests del tipo Superficie (D13, deuda del 1b con dueño 3, tarea 2.3):
construcción, serialización y comparación, mismo patrón que `test_dinero.py`
pero sin signo y con 8 dígitos enteros (NUMERIC(10,2), L-008)."""

import math

import pytest

ACEPTADOS = ["0", "0.00", "45", "45.00", "60.5", "12.50", "99999999", "99999999.99"]
RECHAZADOS_NO_STR = [0.1, 100, True, False, None]
RECHAZADOS_TEXTO = [
    "",
    " 1.00",
    "1.00 ",
    "1,50",
    "+1",
    "1e3",
    "NaN",
    "Infinity",
    "-Infinity",
    "-0",
    "-0.00",
    "-1.00",
    "1.005",
    "100000000",  # 9 dígitos enteros
    "100000000.00",
]

_NO_ASCII = ["٤٥.٠٠", "４５.００"]  # noqa: RUF001 - equivalentes a "45.00"

_SUFIJOS_PELIGROSOS = ["\n", "\r", "\t", " ", "\x00"]
_PREFIJOS_PELIGROSOS = ["\n", "\r", "\t", " ", "\x00"]


@pytest.mark.parametrize("texto", ACEPTADOS)
def test_construccion_acepta_textos_validos(texto: str) -> None:
    from proptech_core.compartido.superficie import Superficie

    Superficie(texto)


@pytest.mark.parametrize("valor", RECHAZADOS_NO_STR)
def test_construccion_rechaza_tipos_que_no_son_str(valor: object) -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    with pytest.raises(SuperficieInvalida):
        Superficie(valor)  # type: ignore[arg-type]


@pytest.mark.parametrize("texto", RECHAZADOS_TEXTO)
def test_construccion_rechaza_textos_invalidos(texto: str) -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    with pytest.raises(SuperficieInvalida):
        Superficie(texto)


def test_nan_e_infinito_como_float_no_rompen_por_otra_via() -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    assert math.isnan(float("nan"))
    with pytest.raises(SuperficieInvalida):
        Superficie(float("nan"))  # type: ignore[arg-type]


@pytest.mark.parametrize("texto", _NO_ASCII)
def test_rechaza_digitos_no_ascii(texto: str) -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    with pytest.raises(SuperficieInvalida):
        Superficie(texto)


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    with pytest.raises(SuperficieInvalida):
        Superficie("45.00" + sufijo)


@pytest.mark.parametrize("prefijo", _PREFIJOS_PELIGROSOS)
def test_rechaza_prefijo_peligroso(prefijo: str) -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    with pytest.raises(SuperficieInvalida):
        Superficie(prefijo + "45.00")


def test_a_texto_siempre_dos_decimales() -> None:
    from proptech_core.compartido.superficie import Superficie

    assert Superficie("45").a_texto() == "45.00"
    assert Superficie("60.5").a_texto() == "60.50"


def test_ida_y_vuelta_por_texto() -> None:
    from proptech_core.compartido.superficie import Superficie

    original = Superficie("12.50")
    reconstruido = Superficie(original.a_texto())
    assert original == reconstruido
    assert original.a_texto() == reconstruido.a_texto()


def test_igualdad_y_hash() -> None:
    from proptech_core.compartido.superficie import Superficie

    a = Superficie("5")
    b = Superficie("5.00")
    assert a == b
    assert hash(a) == hash(b)


def test_superficie_no_es_igual_a_un_float() -> None:
    from proptech_core.compartido.superficie import Superficie

    assert Superficie("0.10") != 0.1


def test_orden() -> None:
    from proptech_core.compartido.superficie import Superficie

    assert Superficie("1.00") < Superficie("2.00")
    assert not (Superficie("2.00") < Superficie("1.00"))


def test_es_inmutable() -> None:
    from proptech_core.compartido.superficie import Superficie

    s = Superficie("1.00")
    with pytest.raises(AttributeError):
        s.decimal = None  # type: ignore[misc, assignment]


def test_superficie_invalida_no_repite_el_texto_recibido() -> None:
    from proptech_core.compartido.superficie import Superficie, SuperficieInvalida

    texto = "secreto-1234"
    with pytest.raises(SuperficieInvalida) as exc_info:
        Superficie(texto)
    assert texto not in str(exc_info.value)
