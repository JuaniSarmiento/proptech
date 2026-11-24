"""Aceptación de H-028: el Excel de la morosidad (change 10a `morosidad`, HIGH; HU-A8, D-167).

Cada test lleva su criterio en el nombre (C01…, N01…) y el escenario de la spec que cubre en su docstring.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import pytest
from openpyxl import load_workbook

from ._h028 import (
    EMAIL_DE_ANA,
    Mundo,
    armar_la_base,
    del_libro,
    morosidad,
    no_encontrado,
    sin_permiso,
)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TITULOS = ["Unidad", "Propietarios", "Situación", "Total vencido", "Capital", "Intereses", "Liquidaciones vencidas",
           "Vencida desde", "Días"]
SITUACION = {"moroso_critico": "Moroso crítico", "con_deuda_vencida": "Con deuda vencida",
             "deuda_de_intereses": "Deuda de intereses", "bajo_umbral": "Bajo el umbral"}


def pedir_excel(m: Mundo, complejo: Any = None) -> Any:
    return m.cliente.get(f"/api/complejos/{complejo or m.edificio}/morosidad/excel")


def hoja(m: Mundo) -> Any:
    r = pedir_excel(m)
    assert r.status_code == 200, f"el Excel: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    libro = load_workbook(BytesIO(r.content))
    assert libro.sheetnames == ["Morosidad"], libro.sheetnames
    return libro["Morosidad"]


def fecha_de(valor: Any) -> date | None:
    if valor is None:
        return None
    assert isinstance(valor, (date, datetime)), f"se esperaba una celda de fecha: {valor!r}"
    return valor.date() if isinstance(valor, datetime) else valor


def monto(celda: Any) -> Decimal:
    assert isinstance(celda.value, (int, float)) and not isinstance(celda.value, bool), (
        f"{celda.coordinate} tiene que ser un número, no {celda.value!r}")
    assert "#,##0.00" in celda.number_format, f"{celda.coordinate}: formato {celda.number_format!r}"
    return Decimal(str(celda.value)).quantize(Decimal("0.01"))


def test_c01_baja_un_xlsx_con_el_encabezado_y_los_titulos(mundo: Mundo) -> None:
    armar_la_base(mundo)
    r = pedir_excel(mundo)
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert r.headers["content-type"].startswith(XLSX), r.headers["content-type"]
    disposicion = r.headers.get("content-disposition", "")
    assert disposicion.startswith("attachment") and 'filename="morosidad-torre-ficticia-2026-11-18.xlsx"' in disposicion, (
        disposicion)
    h = hoja(mundo)
    assert (h["A1"].value, h["B1"].value) == ("Morosidad", "Torre Ficticia"), (h["A1"].value, h["B1"].value)
    assert h["A2"].value == "Fecha" and fecha_de(h["B2"].value) == date(2026, 11, 18), h["B2"].value
    assert h["A3"].value == "Intereses al" and fecha_de(h["B3"].value) == date(2026, 10, 31), h["B3"].value
    assert [c.value for c in h[5][:9]] == TITULOS, [c.value for c in h[5][:9]]


def test_c02_celda_por_celda_igual_a_la_api(mundo: Mundo) -> None:
    """Escenario: Celda por celda"""
    armar_la_base(mundo)
    api = morosidad(mundo)["unidades"]
    h = hoja(mundo)
    assert len(api) == 4, "precondición: la base tiene cuatro unidades con deuda"
    for i, fila in enumerate(api):
        n = 6 + i
        assert h[f"A{n}"].value == fila["unidad"], f"fila {n}: {h[f'A{n}'].value} != {fila['unidad']}"
        assert (h[f"B{n}"].value or "") == ", ".join(fila["propietarios"]), h[f"B{n}"].value
        assert h[f"C{n}"].value == SITUACION[fila["etiqueta"]], h[f"C{n}"].value
        for col, clave in (("D", "total_vencido"), ("E", "capital"), ("F", "intereses")):
            assert monto(h[f"{col}{n}"]) == Decimal(fila[clave]), f"{col}{n} != {clave} de {fila['unidad']}"
        assert h[f"G{n}"].value == fila["liquidaciones_vencidas"], h[f"G{n}"].value
        assert fecha_de(h[f"H{n}"].value) == date.fromisoformat(fila["vencida_desde"]), h[f"H{n}"].value
        assert h[f"I{n}"].value == fila["dias"], h[f"I{n}"].value


def test_c03_la_fila_de_totales_es_el_resumen(mundo: Mundo) -> None:
    armar_la_base(mundo)
    cuerpo = morosidad(mundo)
    h = hoja(mundo)
    n = 6 + len(cuerpo["unidades"])
    assert h[f"A{n}"].value == "Total", h[f"A{n}"].value
    assert monto(h[f"D{n}"]) == Decimal(cuerpo["resumen"]["total_vencido"]), h[f"D{n}"].value
    for col, clave in (("E", "capital"), ("F", "intereses")):
        suma = sum((Decimal(f[clave]) for f in cuerpo["unidades"]), Decimal("0.00"))
        assert monto(h[f"{col}{n}"]) == suma, f"{col}{n}: {h[f'{col}{n}'].value} != {suma}"
    assert h[f"A{n + 1}"].value is None, "después del total no hay más filas"


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio", "contador",
                                 "contador_del_edificio"])
def test_c04_exportan_los_perfiles_de_la_administracion(mundo: Mundo, rol: str) -> None:
    armar_la_base(mundo)
    mundo.como(rol)
    assert hoja(mundo)["A6"].value == "1A"


def test_c04_exportar_morosidad_es_vocabulario_de_auditoria(mundo: Mundo) -> None:
    filas_ = mundo.filas("SELECT nombre FROM accion_de_auditoria WHERE nombre = 'exportar_morosidad'")
    assert len(filas_) == 1, "la migración suma `exportar_morosidad` al vocabulario de auditoría"


def test_c05_sin_deuda_vencida_baja_los_titulos_y_el_total_en_cero(mundo: Mundo) -> None:
    h = hoja(mundo)
    assert [c.value for c in h[5][:9]] == TITULOS
    assert h["A6"].value == "Total", h["A6"].value
    for col in ("D", "E", "F"):
        assert monto(h[f"{col}6"]) == Decimal("0.00"), h[f"{col}6"].value
    assert h["B3"].value is None, "sin intereses registrados, la fecha de los intereses va vacía"


@pytest.mark.parametrize("rol", ["auxiliar", "consejo", "ana"])
def test_n01_auxiliar_consejo_y_vecino_no_exportan(mundo: Mundo, rol: str) -> None:
    """Escenario: El consejo ve pero no exporta"""
    armar_la_base(mundo)
    mundo.como(rol)
    if rol in ("auxiliar", "consejo"):
        assert morosidad(mundo)["unidades"], "precondición: ve la morosidad"
    sin_permiso(pedir_excel(mundo), "exportar_morosidad")


@pytest.mark.parametrize("rol", ["admin_de_otro_edificio", "administracion_b"])
def test_n01_fuera_del_alcance_da_404(mundo: Mundo, rol: str) -> None:
    armar_la_base(mundo)
    mundo.como(rol)
    no_encontrado(pedir_excel(mundo))


def test_n02_ningun_monto_va_como_texto_ni_como_formula(mundo: Mundo) -> None:
    armar_la_base(mundo)
    h = hoja(mundo)
    filas_de_montos = range(6, 6 + len(morosidad(mundo)["unidades"]) + 1)  # las unidades y el total
    for n in filas_de_montos:
        for col in ("D", "E", "F"):
            celda = h[f"{col}{n}"]
            assert not (isinstance(celda.value, str) and celda.value.startswith("=")), f"{col}{n} es una fórmula"
            monto(celda)


def test_n03_no_trae_el_email_de_nadie(mundo: Mundo) -> None:
    armar_la_base(mundo)
    h = hoja(mundo)
    textos = [str(c.value).lower() for fila in h.iter_rows() for c in fila if c.value is not None]
    assert not any(EMAIL_DE_ANA in t or "@" in t for t in textos), "el Excel no lleva emails"


def test_n04_bajar_el_excel_no_escribe(mundo: Mundo) -> None:
    armar_la_base(mundo)
    antes = del_libro(mundo)
    for rol in ("admin_principal", "contador"):
        mundo.como(rol)
        r = pedir_excel(mundo)
        assert r.status_code == 200, f"{rol}: se esperaba 200, llegó {r.status_code}: {r.text[:200]}"
    mundo.como("consejo")
    pedir_excel(mundo)
    assert del_libro(mundo) == antes, "bajar el Excel escribió en el libro o en la auditoría"


def test_n04_otra_administracion_no_baja_su_edificio(mundo: Mundo) -> None:
    mundo.como("super_admin")
    no_encontrado(pedir_excel(mundo, mundo.edificio_b))
