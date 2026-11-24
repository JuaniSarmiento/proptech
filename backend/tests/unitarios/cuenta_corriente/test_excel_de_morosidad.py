"""El libro de la morosidad (10a, H-028): el slug del archivo y el armado de la hoja, sin base."""

from datetime import date
from io import BytesIO
from uuid import uuid4

import pytest
from openpyxl import load_workbook

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.adaptadores.excel_de_morosidad import (
    armar_libro,
    nombre_del_archivo,
)
from proptech_core.cuenta_corriente.aplicacion.morosidad import FilaDeMorosidad, Morosidad


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("Torre Ficticia", "morosidad-torre-ficticia-2026-11-18.xlsx"),
        ("  Edificio Ñandú & Hijos!! ", "morosidad-edificio-nandu-hijos-2026-11-18.xlsx"),
        ("Álamos  del---Sol", "morosidad-alamos-del-sol-2026-11-18.xlsx"),
    ],
)
def test_el_nombre_del_archivo_usa_el_slug_del_edificio(nombre: str, esperado: str) -> None:
    assert nombre_del_archivo(nombre, date(2026, 11, 18)) == esperado


def _fila(unidad: str, total: str, capital: str, intereses: str) -> FilaDeMorosidad:
    return FilaDeMorosidad(
        unidad_id=uuid4(),
        unidad=unidad,
        propietarios=("Ana", "Beto"),
        etiqueta="moroso_critico",
        total_vencido=Dinero(total),
        capital=Dinero(capital),
        intereses=Dinero(intereses),
        liquidaciones_vencidas=2,
        vencida_desde=date(2026, 9, 10),
        dias=69,
    )


def test_el_libro_suma_las_filas_y_deja_los_montos_como_numeros() -> None:
    m = Morosidad(
        fecha=date(2026, 11, 18),
        intereses_al=None,
        unidades=(_fila("1A", "110.50", "100.00", "10.50"), _fila("2B", "0.10", "0.10", "0.00")),
    )
    h = load_workbook(BytesIO(armar_libro("Torre", m)))["Morosidad"]
    assert h["B3"].value is None
    assert h["A8"].value == "Total"
    assert (h["D8"].value, h["E8"].value, h["F8"].value) == (110.6, 100.1, 10.5)
    assert h["B6"].value == "Ana, Beto" and h["C6"].value == "Moroso crítico"
