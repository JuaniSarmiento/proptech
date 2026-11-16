"""El contenido del PDF de la expensa, sin base ni WeasyPrint (7, H-015, R19, D-160)."""

from datetime import date
from typing import Any

import pytest

from proptech_core.liquidacion.dominio.documento import (
    codigo_de_transferencia,
    fecha_corta,
    html_de_la_expensa,
    monto_para_el_pdf,
    periodo_en_palabras,
)


@pytest.mark.parametrize(
    ("nombre", "identificador", "esperado"),
    [
        ("Torre Ficticia", "1B", "TF-1B"),
        ("torre ficticia", "PB 3", "TF-PB 3"),
        ("Edificio  del   Sol", "2A", "EDS-2A"),
        ("Álamos Ñandú", "10", "AN-10"),
        ("Las Heras 123", "4C", "LH1-4C"),
        ("  Torre Ficticia  ", "1B", "TF-1B"),
    ],
)
def test_el_codigo_de_transferencia_son_las_iniciales_mas_el_identificador(
    nombre: str, identificador: str, esperado: str
) -> None:
    assert codigo_de_transferencia(nombre, identificador) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("48350.00", "48.350,00"),
        ("0.00", "0,00"),
        ("5.50", "5,50"),
        ("999.99", "999,99"),
        ("1000.00", "1.000,00"),
        ("1234567.89", "1.234.567,89"),
        ("-1350.00", "-1.350,00"),
        ("33350.00", "33.350,00"),
    ],
)
def test_los_montos_van_con_punto_de_miles_y_coma_decimal(texto: str, esperado: str) -> None:
    assert monto_para_el_pdf(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "1,50", "1.5", "1e3", "--1.00", "1.000"])
def test_un_monto_que_no_viene_como_texto_con_dos_decimales_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError, match="monto"):
        monto_para_el_pdf(texto)


def test_un_monto_no_acepta_float() -> None:
    with pytest.raises(ValueError, match="monto"):
        monto_para_el_pdf(1350.0)  # type: ignore[arg-type]


def test_el_periodo_y_las_fechas_en_castellano() -> None:
    assert periodo_en_palabras(date(2026, 11, 1)) == "noviembre de 2026"
    assert periodo_en_palabras(date(2027, 3, 1)) == "marzo de 2027"
    assert fecha_corta(date(2026, 11, 10)) == "10/11/2026"
    assert fecha_corta(date(2026, 1, 5)) == "05/01/2026"


def _liquidacion() -> dict[str, Any]:
    return {
        "periodo": "2026-11-01",
        "vencimiento": "2026-11-10",
        "bloques": {
            "ordinario": {
                "subtotal": "130000.00",
                "categorias": [
                    {"nombre": "Limpieza", "importe": "90000.00"},
                    {"nombre": "Ascensor", "importe": "40000.00"},
                ],
            },
            "extraordinario": {
                "subtotal": "50000.00",
                "categorias": [{"nombre": "Pintura <del hall>", "importe": "50000.00"}],
            },
        },
        "grupos": [
            {"grupo_id": "g1", "nombre": "Generales"},
            {"grupo_id": "g2", "nombre": "Ascensor"},
        ],
        "unidades": [
            {
                "unidad_id": "u1",
                "identificador": "1B",
                "ordinaria": "27000.00",
                "fondo_de_reserva": "1350.00",
                "extraordinaria": "15000.00",
                "cargos_particulares": [{"concepto": "Multa", "importe": "5000.00"}],
                "intereses": "0.00",
                "total": "48350.00",
                "sin_obligacion": False,
                "saldo_anterior": "0.00",
                "por_grupo": [
                    {"grupo_id": "g1", "ordinaria": "27000.00", "extraordinaria": "15000.00"}
                ],
            }
        ],
    }


def test_la_variante_completa_trae_todo_lo_guardado() -> None:
    html = html_de_la_expensa(
        _liquidacion(), unidad_id="u1", nombre_del_edificio="Torre Ficticia", variante="completa"
    )
    for esperado in (
        "Torre Ficticia", "1B", "TF-1B", "noviembre de 2026", "10/11/2026", "Ordinaria",
        "Extraordinaria", "Limpieza", "Ascensor", "Multa", "5.000,00", "27.000,00", "1.350,00",
        "15.000,00", "48.350,00", "Saldo anterior", "0,00",
    ):  # fmt: skip
        assert esperado in html, esperado


def test_la_variante_sin_extraordinaria_no_la_menciona_y_resta_su_importe() -> None:
    html = html_de_la_expensa(
        _liquidacion(),
        unidad_id="u1",
        nombre_del_edificio="Torre Ficticia",
        variante="sin_extraordinaria",
    )
    assert "33.350,00" in html and "TF-1B" in html and "Ordinaria" in html
    for ausente in ("Pintura", "15.000,00", "48.350,00", "Extraordinaria", "50.000,00"):
        assert ausente not in html, ausente


def test_el_contenido_se_escapa() -> None:
    html = html_de_la_expensa(
        _liquidacion(), unidad_id="u1", nombre_del_edificio="A & <B>", variante="completa"
    )
    assert "A &amp; &lt;B&gt;" in html and "<B>" not in html
    assert "Pintura &lt;del hall&gt;" in html


def test_una_unidad_inexistente_o_una_variante_desconocida_se_rechazan() -> None:
    with pytest.raises(ValueError, match="unidad"):
        html_de_la_expensa(
            _liquidacion(), unidad_id="x", nombre_del_edificio="T", variante="completa"
        )
    with pytest.raises(ValueError, match="variante"):
        html_de_la_expensa(_liquidacion(), unidad_id="u1", nombre_del_edificio="T", variante="otra")
