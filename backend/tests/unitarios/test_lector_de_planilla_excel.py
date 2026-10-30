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
