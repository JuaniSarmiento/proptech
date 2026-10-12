"""Tests del tipo Dinero (D5): construcción, serialización y comparación."""

import math

import pytest

ACEPTADOS = ["20000", "20000.5", "-730.00", "123456789012", "123456789012.34"]
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
    "1.005",
    "1234567890123",  # 13 dígitos enteros
    "1234567890123.00",
]


@pytest.mark.parametrize("texto", ACEPTADOS)
def test_construccion_acepta_textos_validos(texto: str) -> None:
    from proptech_core.compartido.dinero import Dinero

    Dinero(texto)


@pytest.mark.parametrize("valor", RECHAZADOS_NO_STR)
def test_construccion_rechaza_tipos_que_no_son_str(valor: object) -> None:
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero(valor)  # type: ignore[arg-type]


@pytest.mark.parametrize("texto", RECHAZADOS_TEXTO)
def test_construccion_rechaza_textos_invalidos(texto: str) -> None:
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero(texto)


def test_nan_e_infinito_como_float_no_rompen_por_otra_via(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    assert math.isnan(float("nan"))
    with pytest.raises(MontoInvalido):
        Dinero(float("nan"))  # type: ignore[arg-type]


# --- 3.3: serialización y comparación ---


def test_a_texto_siempre_dos_decimales() -> None:
    from proptech_core.compartido.dinero import Dinero

    assert Dinero("20000").a_texto() == "20000.00"
    assert Dinero("20000.5").a_texto() == "20000.50"
    assert Dinero("-730.00").a_texto() == "-730.00"


def test_cero_negativo_se_normaliza_a_cero_positivo() -> None:
    from proptech_core.compartido.dinero import Dinero

    assert Dinero("-0").a_texto() == "0.00"
    assert Dinero("-0.00").a_texto() == "0.00"


def test_ida_y_vuelta_por_texto() -> None:
    from proptech_core.compartido.dinero import Dinero

    original = Dinero("12345.67")
    reconstruido = Dinero(original.a_texto())
    assert original == reconstruido
    assert original.a_texto() == reconstruido.a_texto()


def test_igualdad_y_hash_de_cinco_y_cinco_con_decimales() -> None:
    from proptech_core.compartido.dinero import Dinero

    a = Dinero("5")
    b = Dinero("5.00")
    assert a == b
    assert hash(a) == hash(b)


def test_dinero_no_es_igual_a_un_float() -> None:
    from proptech_core.compartido.dinero import Dinero

    assert Dinero("0.10") != 0.1


def test_orden_entre_montos() -> None:
    from proptech_core.compartido.dinero import Dinero

    assert Dinero("1.00") < Dinero("2.00")
    assert Dinero("-5.00") < Dinero("0.00")
    assert not (Dinero("2.00") < Dinero("1.00"))


def test_typeerror_al_ordenar_contra_otro_tipo() -> None:
    from proptech_core.compartido.dinero import Dinero

    with pytest.raises(TypeError):
        assert Dinero("1.00") < 1


def test_no_existe_suma_ni_resta() -> None:
    from proptech_core.compartido.dinero import Dinero

    a = Dinero("1.00")
    b = Dinero("2.00")
    with pytest.raises(TypeError):
        a + b  # type: ignore[operator]
    with pytest.raises(TypeError):
        a - b  # type: ignore[operator]


def test_repr_y_str() -> None:
    from proptech_core.compartido.dinero import Dinero

    d = Dinero("20000")
    assert repr(d) == 'Dinero("20000.00")'
    assert str(d) == "20000.00"


def test_es_inmutable() -> None:
    from proptech_core.compartido.dinero import Dinero

    d = Dinero("1.00")
    with pytest.raises(AttributeError):
        d.decimal = None  # type: ignore[misc, assignment]


# --- 6.4: MontoInvalido no repite el texto recibido (D5) ---


@pytest.mark.parametrize("texto", ["1,50", "secreto-1234", " 1.00", "1e3"])
def test_monto_invalido_no_repite_el_texto_recibido(texto: str) -> None:
    """El mismo tipo valida campos de `parametros.yaml`; su mensaje no puede
    filtrar contenido del archivo (L-002)."""
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido) as exc_info:
        Dinero(texto)

    assert texto not in str(exc_info.value)


# --- cambio 1b vuelta 4: desde_decimal valida en vez de redondear en silencio ---


def test_desde_decimal_acepta_hasta_dos_decimales_exactos() -> None:
    from decimal import Decimal

    from proptech_core.compartido.dinero import Dinero

    assert Dinero.desde_decimal(Decimal("1.2")).a_texto() == "1.20"
    assert Dinero.desde_decimal(Decimal("1.20")).a_texto() == "1.20"
    assert Dinero.desde_decimal(Decimal("5")).a_texto() == "5.00"


def test_desde_decimal_rechaza_mas_de_dos_decimales_en_vez_de_redondear() -> None:
    """Antes, `Decimal("12.345").quantize(...)` redondeaba en silencio a
    `12.34` pese a que el docstring decía que `desde_decimal` "valida a lo
    sumo dos decimales"."""
    from decimal import Decimal

    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero.desde_decimal(Decimal("12.345"))


def test_desde_decimal_rechaza_un_numero_que_agota_la_precision_del_contexto() -> None:
    """Antes, `Decimal("1e30").quantize(...)` levantaba `decimal.InvalidOperation`
    sin atrapar, en vez de `MontoInvalido` como cualquier otro monto inválido."""
    from decimal import Decimal

    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero.desde_decimal(Decimal("1e30"))


def test_desde_decimal_rechaza_mas_de_doce_digitos_enteros() -> None:
    from decimal import Decimal

    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero.desde_decimal(Decimal("1234567890123"))  # 13 dígitos enteros
