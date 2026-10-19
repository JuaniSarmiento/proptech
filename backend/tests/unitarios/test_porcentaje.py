"""Tests del tipo Porcentaje (D13, deuda del 1b con dueño 3, tarea 2.3):
construcción, serialización y comparación, mismo patrón que `test_dinero.py`
pero sin signo (L-008)."""

import math

import pytest

ACEPTADOS = ["0", "0.00", "3", "3.00", "10", "100", "100.00", "999.99", "0.5", "7.1"]
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
    "1000",  # 4 dígitos enteros
    "1000.00",
]

# Dígitos arábigo-índicos (U+0660..0669) y de ancho completo (U+FF10..FF19),
# categoría Unicode Nd, matcheados por `\d` sin `re.ASCII` (L-008, mismo
# problema que `dinero.py`, rompedor cambio 1b vuelta 2).
_NO_ASCII = ["٣.٠٠", "３.００"]  # noqa: RUF001 - equivalentes a "3.00"

_SUFIJOS_PELIGROSOS = ["\n", "\r", "\t", " ", "\x00"]
_PREFIJOS_PELIGROSOS = ["\n", "\r", "\t", " ", "\x00"]


@pytest.mark.parametrize("texto", ACEPTADOS)
def test_construccion_acepta_textos_validos(texto: str) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    Porcentaje(texto)


@pytest.mark.parametrize("valor", RECHAZADOS_NO_STR)
def test_construccion_rechaza_tipos_que_no_son_str(valor: object) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    with pytest.raises(PorcentajeInvalido):
        Porcentaje(valor)  # type: ignore[arg-type]


@pytest.mark.parametrize("texto", RECHAZADOS_TEXTO)
def test_construccion_rechaza_textos_invalidos(texto: str) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    with pytest.raises(PorcentajeInvalido):
        Porcentaje(texto)


def test_nan_e_infinito_como_float_no_rompen_por_otra_via() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    assert math.isnan(float("nan"))
    with pytest.raises(PorcentajeInvalido):
        Porcentaje(float("nan"))  # type: ignore[arg-type]


@pytest.mark.parametrize("texto", _NO_ASCII)
def test_rechaza_digitos_no_ascii(texto: str) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    with pytest.raises(PorcentajeInvalido):
        Porcentaje(texto)


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    with pytest.raises(PorcentajeInvalido):
        Porcentaje("3.00" + sufijo)


@pytest.mark.parametrize("prefijo", _PREFIJOS_PELIGROSOS)
def test_rechaza_prefijo_peligroso(prefijo: str) -> None:
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    with pytest.raises(PorcentajeInvalido):
        Porcentaje(prefijo + "3.00")


def test_a_texto_siempre_dos_decimales() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    assert Porcentaje("3").a_texto() == "3.00"
    assert Porcentaje("100").a_texto() == "100.00"
    assert Porcentaje("0.5").a_texto() == "0.50"


def test_ida_y_vuelta_por_texto() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    original = Porcentaje("12.34")
    reconstruido = Porcentaje(original.a_texto())
    assert original == reconstruido
    assert original.a_texto() == reconstruido.a_texto()


def test_igualdad_y_hash() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    a = Porcentaje("5")
    b = Porcentaje("5.00")
    assert a == b
    assert hash(a) == hash(b)


def test_porcentaje_no_es_igual_a_un_float() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    assert Porcentaje("0.10") != 0.1


def test_orden() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    assert Porcentaje("1.00") < Porcentaje("2.00")
    assert not (Porcentaje("2.00") < Porcentaje("1.00"))


def test_es_inmutable() -> None:
    from proptech_core.compartido.porcentaje import Porcentaje

    p = Porcentaje("1.00")
    with pytest.raises(AttributeError):
        p.decimal = None  # type: ignore[misc, assignment]


def test_porcentaje_invalido_no_repite_el_texto_recibido() -> None:
    """Mismo motivo que `Dinero` (L-002): este tipo valida campos de
    `parametros.yaml`, su mensaje no puede filtrar contenido del archivo."""
    from proptech_core.compartido.porcentaje import Porcentaje, PorcentajeInvalido

    texto = "secreto-1234"
    with pytest.raises(PorcentajeInvalido) as exc_info:
        Porcentaje(texto)
    assert texto not in str(exc_info.value)
