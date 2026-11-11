"""5.6: el adaptador real de `LectorDePlanillaDeCargos` (openpyxl)."""

import io

import pytest
from openpyxl import Workbook

from proptech_core.gastos.adaptadores.excel import LectorDePlanillaExcel, PlanillaInvalida


def _planilla(filas: list[tuple[object, object, object]]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    assert hoja is not None
    hoja.append(["unidad", "concepto", "importe"])
    for fila in filas:
        hoja.append(list(fila))
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def test_lee_tres_filas_validas() -> None:
    contenido = _planilla(
        [("1A", "Expensa extra", "1000.00"), ("1B", "Multa", "500.00"), ("2A", "Quincho", "200")]
    )
    filas = LectorDePlanillaExcel().leer(contenido)
    assert [f.unidad_identificador for f in filas] == ["1A", "1B", "2A"]
    assert [f.numero_de_fila for f in filas] == [2, 3, 4]
    assert filas[0].concepto == "Expensa extra"
    assert filas[0].importe == "1000.00"


def test_fila_con_celdas_vacias_llega_como_none() -> None:
    contenido = _planilla([(None, None, None)])
    filas = LectorDePlanillaExcel().leer(contenido)
    assert filas[0].unidad_identificador is None
    assert filas[0].concepto is None
    assert filas[0].importe is None


def test_planilla_corrupta_da_planilla_invalida() -> None:
    with pytest.raises(PlanillaInvalida):
        LectorDePlanillaExcel().leer(b"esto no es un xlsx")


def test_hoja_vacia_sin_encabezado_devuelve_lista_vacia() -> None:
    libro = Workbook()
    buffer = io.BytesIO()
    libro.save(buffer)
    filas = LectorDePlanillaExcel().leer(buffer.getvalue())
    assert filas == []


# --- importacion-desde-excel 1.2 (D2 del 6, L-066): el docstring promete una
# conducta de la librería y se prueba contra la librería. ---


def _con_formula(contenido: bytes, celda: str, formula: str, cache: str | None) -> bytes:
    import re
    import zipfile

    entrada = zipfile.ZipFile(io.BytesIO(contenido))
    ruta = "xl/worksheets/sheet1.xml"
    xml = entrada.read(ruta).decode()
    nueva = f'<c r="{celda}"><f>{formula}</f>' + (f"<v>{cache}</v>" if cache else "") + "</c>"
    xml, cambios = re.subn(rf'<c r="{celda}"[^>]*?(?:/>|>.*?</c>)', nueva, xml, count=1, flags=re.S)
    assert cambios == 1
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as nuevo:
        for item in entrada.infolist():
            nuevo.writestr(item, xml if item.filename == ruta else entrada.read(item.filename))
    return salida.getvalue()


def test_una_formula_con_valor_en_cache_entra_por_su_valor() -> None:
    contenido = _con_formula(_planilla([("1A", "Multa", "999")]), "C2", "400+100", "500")
    filas = LectorDePlanillaExcel().leer(contenido)
    assert [f.importe for f in filas] == ["500"]


def test_una_formula_sin_valor_en_cache_entra_como_celda_vacia() -> None:
    contenido = _con_formula(_planilla([("1A", "Multa", "999")]), "C2", "400+100", None)
    filas = LectorDePlanillaExcel().leer(contenido)
    assert [f.importe for f in filas] == [None]
