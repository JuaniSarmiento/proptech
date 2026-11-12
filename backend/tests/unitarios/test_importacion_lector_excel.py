"""Tarea 1.2 de `importacion-desde-excel`: el lector de la plantilla (design D1, D2, D3, E9, E14).

Los `.xlsx` se arman en el test con `openpyxl`; los datos son inventados."""

from __future__ import annotations

import datetime
import io
import re
import zipfile
from typing import Any

import pytest
from openpyxl import Workbook

from proptech_core.importacion.adaptadores.excel import LectorDePlantillaExcel
from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    LIMITE_DE_BYTES,
    LIMITE_DE_FILAS,
    ArchivoInvalido,
    HojaLeida,
)

UNIDADES = ENCABEZADOS_POR_HOJA["Unidades"]


def _libro(hojas: dict[str, list[list[Any]]]) -> bytes:
    libro = Workbook()
    primera = True
    for nombre, filas in hojas.items():
        hoja = libro.active if primera else libro.create_sheet()
        assert hoja is not None
        hoja.title = nombre
        primera = False
        for fila in filas:
            hoja.append(fila)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _unidades(*filas: list[Any], encabezados: tuple[str, ...] = UNIDADES) -> bytes:
    return _libro({"Unidades": [list(encabezados), *filas]})


def _fila_valida(unidad: str = "1A", **cambios: Any) -> list[Any]:
    base = {
        "Unidad": unidad,
        "Tipo": "departamento",
        "Piso": "1",
        "Coeficiente": "0,083333",
        "Superficie m2": "45.50",
        "Propietario": "Persona Ficticia Uno",
        "Email": "uno@ficticio.test",
    }
    base.update(cambios)
    return [base[c] for c in UNIDADES]


def _hoja(contenido: bytes, nombre: str) -> HojaLeida:
    hoja = LectorDePlantillaExcel().leer(contenido).hojas.get(nombre)
    assert hoja is not None, f"el lector no devolvió la hoja {nombre}"
    return hoja


def _unidades_leidas(contenido: bytes) -> HojaLeida:
    return _hoja(contenido, "Unidades")


def _rechazo(contenido: bytes, nombre: str | None = None) -> ArchivoInvalido:
    with pytest.raises(ArchivoInvalido) as error:
        LectorDePlantillaExcel().leer(contenido, nombre=nombre)
    return error.value


def _con_formula(contenido: bytes, celda: str, formula: str, cache: str | None) -> bytes:
    """`openpyxl` no guarda nunca el valor en caché: se edita el XML a mano."""
    entrada = zipfile.ZipFile(io.BytesIO(contenido))
    ruta = "xl/worksheets/sheet1.xml"
    xml = entrada.read(ruta).decode()
    nueva = f'<c r="{celda}"><f>{formula}</f>' + (f"<v>{cache}</v>" if cache else "") + "</c>"
    xml, cambios = re.subn(rf'<c r="{celda}"[^>]*?(?:/>|>.*?</c>)', nueva, xml, count=1, flags=re.S)
    assert cambios == 1, f"no encontré la celda {celda}"
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as nuevo:
        for item in entrada.infolist():
            nuevo.writestr(item, xml if item.filename == ruta else entrada.read(item.filename))
    return salida.getvalue()


# --- Hojas y encabezados por nombre, nunca por posición ----------------------------------------


def test_columnas_en_otro_orden_se_leen_igual() -> None:
    """Escenario: Columnas en otro orden"""
    otro_orden = (
        "Email",
        "Piso",
        "Unidad",
        "Superficie m2",
        "Tipo",
        "Coeficiente",
        "Propietario",
    )
    valores = _fila_valida("2B")
    por_nombre = dict(zip(UNIDADES, valores, strict=True))
    fila_en_otro_orden = [por_nombre[c] for c in otro_orden]
    hoja = _unidades_leidas(_unidades(fila_en_otro_orden, encabezados=otro_orden))
    assert hoja.encabezados == otro_orden
    assert [dict(f.valores) for f in hoja.filas] == [por_nombre]


def test_las_columnas_extra_se_ignoran() -> None:
    encabezados = ("Notas", *UNIDADES, "Otra")
    hoja = _unidades_leidas(_unidades(["a mano", *_fila_valida(), "x"], encabezados=encabezados))
    assert len(hoja.filas) == 1
    assert set(hoja.filas[0].valores) == set(UNIDADES)
    assert hoja.encabezados == UNIDADES


@pytest.mark.parametrize("mal", ["Coeficiente ", "coeficiente", "Coef.", "COEFICIENTE"])
def test_un_encabezado_con_otro_nombre_no_cuenta(mal: str) -> None:
    """Escenario: Falta un encabezado (el lector informa lo que hay; el rechazo es de `padron`)."""
    encabezados = tuple(mal if c == "Coeficiente" else c for c in UNIDADES)
    hoja = _unidades_leidas(_unidades(_fila_valida(), encabezados=encabezados))
    assert "Coeficiente" not in hoja.encabezados
    assert hoja.encabezados == tuple(c for c in encabezados if c in UNIDADES)
    assert len(hoja.filas) == 1
    assert "Coeficiente" not in hoja.filas[0].valores
    assert mal not in hoja.filas[0].valores


def test_las_hojas_se_buscan_por_nombre_y_no_por_posicion() -> None:
    contenido = _libro(
        {"Notas": [["Texto"], ["nada"]], "Control": [["Unidad"]], "Unidades": [list(UNIDADES)]}
    )
    plantilla = LectorDePlantillaExcel().leer(contenido)
    assert set(plantilla.hojas) == {"Unidades", "Control"}
    assert plantilla.hojas["Unidades"].encabezados == UNIDADES


@pytest.mark.parametrize("nombre", ["unidades", "Unidades ", "UNIDADES"])
def test_un_nombre_de_hoja_parecido_no_cuenta(nombre: str) -> None:
    contenido = _libro({nombre: [list(UNIDADES), _fila_valida()]})
    assert "Unidades" not in LectorDePlantillaExcel().leer(contenido).hojas


def test_una_hoja_con_solo_encabezados_no_tiene_filas() -> None:
    assert _unidades_leidas(_unidades()).filas == ()


# --- Archivo que no es un Excel, o que pasa un límite -------------------------------------------


@pytest.mark.parametrize(
    "contenido",
    [
        b"Unidad,Tipo\n1A,departamento\n",
        b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\n",
        _unidades(_fila_valida())[:500],
        b"",
    ],
    ids=["csv", "pdf", "xlsx_truncado", "vacio"],
)
def test_no_es_un_excel(contenido: bytes) -> None:
    """Escenario: No es un Excel"""
    error = _rechazo(contenido, nombre="padron-torre-ficticia.xlsx")
    assert len(error.errores) == 1
    [e] = error.errores
    assert e.fila is None
    assert "padron-torre-ficticia.xlsx" in e.motivo
    assert re.search(r"excel|xlsx", e.motivo, re.I)


def test_el_limite_de_bytes_se_chequea_antes_de_abrir_el_archivo() -> None:
    """Escenario: Archivo enorme (bytes). El contenido no es un Excel: si se abriera primero, el
    error sería "no es un Excel" y no el límite."""
    error = _rechazo(b"x" * (LIMITE_DE_BYTES + 1))
    [e] = error.errores
    assert e.fila is None
    assert "2 MiB" in e.motivo


def test_justo_en_el_limite_de_bytes_se_abre_el_archivo() -> None:
    error = _rechazo(b"x" * LIMITE_DE_BYTES)
    assert "2 MiB" not in error.errores[0].motivo


def test_dos_mil_filas_pasan_y_dos_mil_una_no() -> None:
    """Escenario: Archivo enorme (filas)"""
    justas = [_fila_valida(f"U{n}") for n in range(LIMITE_DE_FILAS)]
    assert len(_unidades_leidas(_unidades(*justas)).filas) == 2000
    [e] = _rechazo(_unidades(*justas, _fila_valida("U2000"))).errores
    assert (e.hoja, e.fila) == ("Unidades", None)
    assert "2.000 filas" in e.motivo


def test_las_filas_en_blanco_no_cuentan_para_el_limite() -> None:
    filas = [_fila_valida(f"U{n}") for n in range(LIMITE_DE_FILAS)]
    contenido = _unidades(*filas, *([[None] * 7] * 50))
    assert len(_unidades_leidas(contenido).filas) == LIMITE_DE_FILAS


# --- Filas: número de fila del Excel, vacías y texto exacto -------------------------------------


def test_el_numero_de_fila_es_el_del_excel_y_las_filas_vacias_se_saltean() -> None:
    contenido = _unidades(_fila_valida("1A"), [None] * 7, _fila_valida("1B"))
    assert [(f.numero, f.valores["Unidad"]) for f in _unidades_leidas(contenido).filas] == [
        (2, "1A"),
        (4, "1B"),
    ]


def test_el_texto_llega_exacto_y_la_celda_vacia_es_none() -> None:
    contenido = _unidades(
        _fila_valida("1A", Piso=" PB", Propietario=None, Email=""),
        _fila_valida("1B", Tipo="Departamento", Coeficiente="1.234"),
    )
    filas = _unidades_leidas(contenido).filas
    assert len(filas) == 2
    primera, segunda = filas
    assert primera.valores["Piso"] == " PB"
    assert primera.valores["Propietario"] is None
    assert primera.valores["Email"] is None
    assert segunda.valores["Tipo"] == "Departamento"
    assert segunda.valores["Coeficiente"] == "1.234"


# --- E14: números a Decimal desde repr, nunca float ---------------------------------------------


@pytest.mark.parametrize(
    ("celda", "texto"),
    [
        (8.3e-05, "0.000083"),
        (0.083333, "0.083333"),
        (1e-07, "0.0000001"),
        (45.5, "45.5"),
        (12, "12"),
        (0.3333333333333333, "0.3333333333333333"),
        (1234.56, "1234.56"),
    ],
)
def test_una_celda_numerica_llega_en_notacion_fija_sin_pasar_por_float(
    celda: float, texto: str
) -> None:
    contenido = _unidades(_fila_valida(Coeficiente=celda))
    assert [f.valores["Coeficiente"] for f in _unidades_leidas(contenido).filas] == [texto]


def test_una_fecha_llega_como_fecha_iso() -> None:
    contenido = _libro(
        {
            "Saldos": [
                list(ENCABEZADOS_POR_HOJA["Saldos"]),
                ["1A", None, datetime.datetime(2026, 1, 5), None, None, None],
            ]
        }
    )
    hoja = _hoja(contenido, "Saldos")
    assert [f.valores["Vencimiento"] for f in hoja.filas] == ["2026-01-05"]


# --- D2: fórmulas por su valor en caché; sin caché, error de celda -------------------------------


def test_una_formula_sin_valor_en_cache_queda_marcada() -> None:
    """Escenario: Fórmula sin valor en caché"""
    base = _unidades(_fila_valida(), _fila_valida("1B", **{"Superficie m2": 999}))
    contenido = _con_formula(base, "E3", "40+5", None)
    hoja = _unidades_leidas(contenido)
    assert [(f.numero, f.formulas_sin_cache) for f in hoja.filas] == [
        (2, frozenset()),
        (3, frozenset({"Superficie m2"})),
    ]
    assert hoja.filas[1].valores["Superficie m2"] is None


def test_una_formula_con_valor_en_cache_se_lee_por_su_valor() -> None:
    base = _unidades(_fila_valida("1A", **{"Superficie m2": 999}))
    contenido = _con_formula(base, "E2", "40+5", "45")
    filas = _unidades_leidas(contenido).filas
    assert [(f.valores["Superficie m2"], f.formulas_sin_cache) for f in filas] == [
        ("45", frozenset())
    ]


def test_una_fila_con_solo_una_formula_sin_cache_no_es_una_fila_en_blanco() -> None:
    base = _unidades([None, None, None, None, 999, None, None])
    contenido = _con_formula(base, "E2", "40+5", None)
    hoja = _unidades_leidas(contenido)
    assert [f.numero for f in hoja.filas] == [2]
    assert hoja.filas[0].formulas_sin_cache == {"Superficie m2"}


def test_se_distingue_la_celda_numerica_del_texto_con_el_mismo_aspecto() -> None:
    """Un `0.125` numérico es exacto; el texto `0.125` (o `1.234`) puede ser ambiguo (E14): el
    lector dice cuál es cuál para que `padron` no rechace un número bien escrito."""
    contenido = _unidades(
        _fila_valida("1A", Coeficiente=0.125, **{"Superficie m2": "45.5"}),
        _fila_valida("1B", Coeficiente="0.125", **{"Superficie m2": 45}),
    )
    filas = _unidades_leidas(contenido).filas
    assert [f.numericas for f in filas] == [
        frozenset({"Coeficiente"}),
        frozenset({"Superficie m2"}),
    ]
