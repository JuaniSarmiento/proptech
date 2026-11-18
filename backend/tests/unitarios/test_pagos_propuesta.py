"""La validación de la propuesta que lee la IA, campo por campo (H-019, E5, D-164)."""

from datetime import date

import pytest

from proptech_core.pagos.dominio.propuesta import PROPUESTA_VACIA, validar_propuesta

HOY = date(2026, 11, 18)
BUENA = {
    "banco": "Banco Nación",
    "numero_de_operacion": "12345678",
    "fecha": "2026-11-05",
    "monto": "43350.00",
    "cbu_origen": "0110599520000001234567",
}


def test_una_propuesta_buena_pasa_igual() -> None:
    assert validar_propuesta(BUENA, HOY) == BUENA


def test_las_claves_de_mas_se_ignoran_y_las_que_faltan_son_nulas() -> None:
    resultado = validar_propuesta({"banco": "X", "estado": "confirmado"}, HOY)
    assert resultado == {**PROPUESTA_VACIA, "banco": "X"}


def test_lo_que_no_es_un_objeto_da_la_propuesta_vacia() -> None:
    assert validar_propuesta(["banco"], HOY) == PROPUESTA_VACIA  # type: ignore[arg-type]


def test_el_texto_se_recorta() -> None:
    assert validar_propuesta({**BUENA, "banco": "  Galicia "}, HOY)["banco"] == "Galicia"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("monto", "-10.00"),
        ("monto", "0.00"),
        ("monto", "43.350,00"),
        ("monto", "10"),
        ("monto", 43350.0),
        ("fecha", "2026-11-19"),
        ("fecha", "2025-11-17"),
        ("fecha", "2026-02-30"),
        ("fecha", "05/11/2026"),
        ("cbu_origen", "011059952000000123456"),
        ("cbu_origen", "abcdefghijklmnopqrstuv"),
        ("cbu_origen", 110599520000001234567),
        ("numero_de_operacion", "9" * 101),
        ("numero_de_operacion", "   "),
        ("banco", ["Banco Nación"]),
        ("banco", {"nombre": "x"}),
        ("banco", None),
    ],
)
def test_un_campo_invalido_vuelve_nulo(campo: str, valor: object) -> None:
    assert validar_propuesta({**BUENA, campo: valor}, HOY) == {**BUENA, campo: None}


def test_los_bordes_validos_entran() -> None:
    cruda = {**BUENA, "fecha": "2025-11-18", "numero_de_operacion": "9" * 100, "monto": "0.01"}
    assert validar_propuesta(cruda, HOY) == cruda
    assert validar_propuesta({**BUENA, "fecha": "2026-11-18"}, HOY)["fecha"] == "2026-11-18"
