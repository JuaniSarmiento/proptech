"""H-007 · C09 a C15: lo que tiene que fallar sin escribir nada (0 unidades, 0 personas, 0
importaciones, ninguna auditoría, ninguna invitación)."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any

import pytest

from ._h007 import (
    ENCABEZADOS,
    MIGRACION,
    XLSX,
    Mundo,
    aceptada,
    con_formula,
    conflicto,
    conteos,
    de_fila,
    errores,
    fila_del_excel,
    filas_validas,
    importar,
    libro,
    padron,
    unidades,
)

pytestmark = pytest.mark.integracion


def _rechazado_sin_escribir(
    m: Mundo, complejo: Any, respuesta: Any, antes: dict[str, int]
) -> list[Any]:
    lista = errores(respuesta)
    assert conteos(m) == antes, "un archivo rechazado no escribe nada"
    return lista


def _columna(nombre: str) -> str:
    return "ABCDEFG"[ENCABEZADOS.index(nombre)]


# --- C09 · Errores de archivo ---------------------------------------------------------------------


def _relleno_de(megas: int) -> list[list[Any]]:
    """Filas de texto aleatorio (no se comprime) para pasar `megas` MiB."""
    filas = [["Relleno"]]
    while sum(len(f[0]) for f in filas[1:]) < megas * 2 * 1024 * 1024:
        filas.append([os.urandom(8000).hex()[:16000]])
    return filas


def _archivo(caso: str) -> tuple[bytes, str, Callable[[list[Any]], bool]]:
    """(contenido, nombre del archivo, chequeo del error) de cada caso de archivo."""

    def nombra(*palabras: str) -> Callable[[list[Any]], bool]:
        def chequeo(lista: list[Any]) -> bool:
            texto = [f"{e.hoja} {e.columna} {e.motivo}" for e in lista]
            return any(all(re.search(p, x, re.I) for p in palabras) for x in texto)

        return chequeo

    if caso == "csv":
        return b"Unidad,Tipo\n1A,departamento\n", "padron.csv", nombra("archivo|excel|xlsx")
    if caso == "pdf_renombrado":
        return (
            b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\n",
            ARCHIVO_X,
            nombra("archivo|excel|xlsx"),
        )
    if caso == "xlsx_corrupto":
        return padron()[:500], ARCHIVO_X, nombra("archivo|excel|xlsx")
    if caso == "tres_mib":
        contenido = padron(extra={"Relleno": _relleno_de(3)})
        assert len(contenido) > 3 * 1024 * 1024, f"el relleno no llegó a 3 MiB: {len(contenido)}"
        return contenido, ARCHIVO_X, nombra(r"2 ?MiB|l[ií]mite|tama")
    if caso == "dos_mil_una_filas":
        filas = [
            {**filas_validas()[0], "Unidad": f"U{n}", "Coeficiente": "0.000499"}
            for n in range(2001)
        ]
        return padron(filas), ARCHIVO_X, nombra(r"2\.?000")
    if caso == "sin_hoja_unidades":
        return libro({"Notas": [["Texto"], ["nada"]]}), ARCHIVO_X, nombra("Unidades")
    if caso == "hoja_en_minuscula":
        return padron(nombre_de_hoja="unidades"), ARCHIVO_X, nombra("Unidades")
    if caso == "hoja_con_espacio":
        return padron(nombre_de_hoja="Unidades "), ARCHIVO_X, nombra("Unidades")
    if caso.startswith("encabezado_"):
        mal = {
            "encabezado_faltante": None,
            "encabezado_con_espacio": "Coeficiente ",
            "encabezado_abreviado": "Coef.",
        }[caso]
        encabezados: list[str] = [
            nuevo for c in ENCABEZADOS if (nuevo := (mal if c == "Coeficiente" else c)) is not None
        ]
        filas = [{**f, **({mal: f["Coeficiente"]} if mal else {})} for f in filas_validas()]
        return padron(filas, encabezados=encabezados), ARCHIVO_X, nombra("Unidades", "Coeficiente")
    raise AssertionError(caso)


ARCHIVO_X = "padron-torre-ficticia.xlsx"
CASOS_DE_ARCHIVO = [
    "csv",
    "pdf_renombrado",
    "xlsx_corrupto",
    "tres_mib",
    "dos_mil_una_filas",
    "sin_hoja_unidades",
    "hoja_en_minuscula",
    "hoja_con_espacio",
    "encabezado_faltante",
    "encabezado_con_espacio",
    "encabezado_abreviado",
]


@pytest.mark.parametrize("caso", CASOS_DE_ARCHIVO)
def test_c09_archivo_rechazado_entero(mundo: Mundo, caso: str) -> None:
    """Escenario: No es un Excel
    Escenario: Archivo enorme
    Escenario: Falta un encabezado"""
    contenido, nombre, nombra = _archivo(caso)
    antes = conteos(mundo)
    tipo = "text/csv" if nombre.endswith(".csv") else XLSX
    respuesta = importar(mundo, mundo.torre, contenido, nombre=nombre, tipo=tipo)
    lista = _rechazado_sin_escribir(mundo, mundo.torre, respuesta, antes)
    assert nombra(lista), f"el error no nombra el problema ({caso}): {lista}"
    assert de_fila(lista) == [], f"un error de archivo corta antes de leer filas: {lista}"


@pytest.mark.parametrize(
    ("fecha", "palabra"),
    [
        (None, "fecha_de_migracion"),
        ("2999-01-01", "fecha_de_migracion"),
        ("15/10/2026", "fecha_de_migracion"),
    ],
)
def test_c09_fecha_de_migracion_falta_futura_o_mal_escrita(
    mundo: Mundo, fecha: str | None, palabra: str
) -> None:
    """La fecha de migración se elige al subir, es una fecha ISO y no es posterior a hoy (E15)."""
    antes = conteos(mundo)
    respuesta = importar(mundo, mundo.torre, padron(), fecha=fecha)
    assert respuesta.status_code == 422, (
        f"se esperaba 422, llegó {respuesta.status_code}: {respuesta.text[:300]}"
    )
    assert palabra in respuesta.text, f"el rechazo no nombra `{palabra}`: {respuesta.text[:300]}"
    assert conteos(mundo) == antes


# --- C10 · Errores de fila ------------------------------------------------------------------------

#: (caso, unidad cuya fila se rompe, columna, valor nuevo).
CASOS_DE_FILA: list[tuple[str, str, str, Any]] = [
    ("unidad_vacia", "1C", "Unidad", None),
    ("unidad_de_41", "1C", "Unidad", "X" * 41),
    # Un tab: carácter de control que openpyxl sí deja escribir en una celda.
    ("unidad_con_control", "1C", "Unidad", "1\tC"),
    ("tipo_vacio", "1C", "Tipo", None),
    ("tipo_depto", "1C", "Tipo", "Depto"),
    ("tipo_con_mayuscula", "1C", "Tipo", "Departamento"),
    ("piso_vacio", "1C", "Piso", None),
    ("piso_4", "1C", "Piso", "4"),
    ("piso_ss2", "1C", "Piso", "SS2"),
    ("piso_1_grado", "1C", "Piso", "1°"),
    ("piso_entrepiso", "1C", "Piso", "Entrepiso"),
    ("piso_planta_alta", "1C", "Piso", "planta alta"),
    ("piso_con_espacio", "L1", "Piso", " PB"),
    ("coeficiente_cero", "1C", "Coeficiente", "0"),
    ("coeficiente_negativo", "1C", "Coeficiente", "-0.083333"),
    ("coeficiente_mayor_que_uno", "1C", "Coeficiente", "1.5"),
    ("coeficiente_siete_decimales", "1C", "Coeficiente", "0.0833333"),
    ("coeficiente_ambiguo", "1C", "Coeficiente", "1.234"),
    ("superficie_cero", "1C", "Superficie m2", "0"),
    ("superficie_negativa", "1C", "Superficie m2", "-45.50"),
    ("superficie_tres_decimales", "1C", "Superficie m2", "45.555"),
    ("email_invalido", "1C", "Email", "no-es-un-email"),
]


@pytest.mark.parametrize(
    ("caso", "unidad", "columna", "valor"), CASOS_DE_FILA, ids=[c[0] for c in CASOS_DE_FILA]
)
def test_c10_una_fila_mal_no_carga_nada(
    mundo: Mundo, caso: str, unidad: str, columna: str, valor: Any
) -> None:
    """Escenario: Celda vacía obligatoria
    Escenario: Siete decimales
    Escenario: Email inválido"""
    filas = filas_validas()
    fila = fila_del_excel(unidad)
    filas[fila - 2][columna] = valor
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, padron(filas)), antes
    )
    # Un coeficiente mal también puede romper la suma: ese error es de la hoja, sin fila.
    assert de_fila(lista) == [("Unidades", fila, columna)], f"{caso}: {lista}"


def test_c10_un_solo_error_no_carga_nada(mundo: Mundo) -> None:
    """Escenario: Un solo error no carga nada"""
    filas = filas_validas()
    filas[9 - 2]["Piso"] = "Entrepiso"
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, padron(filas)), antes
    )
    assert de_fila(lista) == [("Unidades", 9, "Piso")], lista
    assert unidades(mundo, mundo.torre) == {}


def test_c10_unidad_repetida_nombra_la_otra_fila(mundo: Mundo) -> None:
    """Escenario: Unidad repetida"""
    filas = filas_validas()
    assert filas[4 - 2]["Unidad"] == "2B"
    filas[11 - 2]["Unidad"] = "2B"
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, padron(filas)), antes
    )
    assert de_fila(lista) == [("Unidades", 11, "Unidad")], lista
    motivo = next(e.motivo for e in lista if e.fila == 11)
    assert re.search(r"\b4\b", motivo), f"el error de la fila 11 nombra la fila 4: {lista}"


def test_c10_piso_fuera_del_vocabulario(mundo: Mundo) -> None:
    """Escenario: Piso fuera del vocabulario"""
    filas = filas_validas()
    filas[fila_del_excel("1A") - 2]["Piso"] = "4"
    filas[fila_del_excel("1B") - 2]["Piso"] = "1°"
    filas[fila_del_excel("L1") - 2]["Piso"] = " PB"
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, padron(filas)), antes
    )
    assert de_fila(lista) == sorted(
        ("Unidades", fila_del_excel(u), "Piso") for u in ("1A", "1B", "L1")
    ), lista


def test_c10_formula_sin_valor_en_cache(mundo: Mundo) -> None:
    """Escenario: Fórmula sin valor en caché"""
    filas = filas_validas()
    filas[fila_del_excel("1B") - 2]["Superficie m2"] = 999
    celda = f"{_columna('Superficie m2')}{fila_del_excel('1B')}"
    contenido = con_formula(padron(filas), celda, "40+5", None)
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, contenido), antes
    )
    assert de_fila(lista) == [("Unidades", fila_del_excel("1B"), "Superficie m2")], lista


# --- C11 · Todos los errores juntos ---------------------------------------------------------------


def test_c11_varios_errores_juntos(mundo: Mundo) -> None:
    """Escenario: Varios errores juntos"""
    filas = filas_validas()
    filas[3 - 2]["Tipo"] = None
    filas[7 - 2]["Superficie m2"] = "0"
    filas[12 - 2]["Email"] = "sin-arroba.test"
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, padron(filas)), antes
    )
    assert de_fila(lista) == [
        ("Unidades", 3, "Tipo"),
        ("Unidades", 7, "Superficie m2"),
        ("Unidades", 12, "Email"),
    ], lista
    assert all(e.motivo.strip() for e in lista), "cada error dice su motivo"


# --- C12 · Suma fuera de la tolerancia ------------------------------------------------------------


@pytest.mark.parametrize(("ultimo", "suma"), [("0.083137", "0,9998"), ("0.083537", "1,0002")])
def test_c12_suma_fuera_de_la_tolerancia(mundo: Mundo, ultimo: str, suma: str) -> None:
    """Escenario: Suma 0,9998"""
    filas = filas_validas()
    filas[11]["Coeficiente"] = ultimo
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.torre, importar(mundo, mundo.torre, padron(filas)), antes
    )
    numero = suma.replace(",", "[.,]")
    assert any(
        re.search(numero, e.motivo) and re.search(r"0[.,]0001|toleranc", e.motivo, re.I)
        for e in lista
    ), f"el error nombra la suma {suma} y la tolerancia: {lista}"
    assert de_fila(lista) == [], "la suma es un error de la hoja, no de una fila"


# --- C13 · Padrón ---------------------------------------------------------------------------------


def test_c13_edificio_sin_pisos_configurados(mundo: Mundo) -> None:
    """Escenario: Edificio sin pisos configurados"""
    antes = conteos(mundo)
    lista = _rechazado_sin_escribir(
        mundo, mundo.sin_pisos, importar(mundo, mundo.sin_pisos, padron()), antes
    )
    assert any(re.search(r"piso", f"{e.columna} {e.motivo}", re.I) for e in lista), lista


def test_c13_padron_sobre_unidades_existentes(mundo: Mundo) -> None:
    """Escenario: Padrón sobre unidades existentes"""
    filas = [f for f in filas_validas() if f["Unidad"] in ("2B", "3A")]
    antes = conteos(mundo)
    previas = unidades(mundo, mundo.con_padron)
    lista = _rechazado_sin_escribir(
        mundo, mundo.con_padron, importar(mundo, mundo.con_padron, padron(filas)), antes
    )
    assert any(e.hoja == "Unidades" for e in lista), lista
    assert unidades(mundo, mundo.con_padron) == previas


def test_c13_unidad_que_ya_existe_en_el_edificio(mundo: Mundo) -> None:
    """`1A` ya existe en el edificio con padrón: la fila es un error y no se toca nada."""
    filas = [{**filas_validas()[0], "Coeficiente": "1"}]
    antes = conteos(mundo)
    previas = unidades(mundo, mundo.con_padron)
    lista = _rechazado_sin_escribir(
        mundo, mundo.con_padron, importar(mundo, mundo.con_padron, padron(filas)), antes
    )
    assert any(e.hoja == "Unidades" for e in lista), lista
    assert unidades(mundo, mundo.con_padron) == previas


# --- C14 · Reimportación --------------------------------------------------------------------------


def test_c14_mismo_archivo_dos_veces(mundo: Mundo) -> None:
    """Escenario: Mismo archivo dos veces"""
    contenido = padron()
    primera = aceptada(importar(mundo, mundo.torre, contenido))
    antes = conteos(mundo)
    segunda = importar(mundo, mundo.torre, contenido)
    cuerpo = conflicto(segunda, "archivo")
    assert str(cuerpo.get("importacion_id")) == str(primera["importacion_id"]), (
        f"el conflicto nombra la importación anterior: {cuerpo}"
    )
    assert conteos(mundo) == antes
    assert len(unidades(mundo, mundo.torre)) == 12


def test_c14_mismo_archivo_con_otro_nombre_tambien(mundo: Mundo) -> None:
    """La huella es de los bytes, no del nombre."""
    contenido = padron()
    aceptada(importar(mundo, mundo.torre, contenido))
    antes = conteos(mundo)
    conflicto(importar(mundo, mundo.torre, contenido, nombre="otro-nombre.xlsx"), "archivo")
    assert conteos(mundo) == antes


# --- C15 · Estado de la migración -----------------------------------------------------------------


@pytest.mark.parametrize("estado", ["confirmada", "sin_saldos_previos"])
def test_c15_importador_cerrado(mundo: Mundo, estado: str) -> None:
    """Escenario: Importador cerrado"""
    mundo.filas(
        "UPDATE complejo SET estado_migracion = %s WHERE id = %s RETURNING id",
        (estado, mundo.torre),
    )
    antes = conteos(mundo)
    conflicto(importar(mundo, mundo.torre, padron()), "estado_migracion")
    assert conteos(mundo) == antes


def test_c15_la_fecha_de_migracion_por_defecto_del_ejemplo_es_valida(mundo: Mundo) -> None:
    """Control: la fecha de la base de los ejemplos se acepta.

    Si no, los rechazos de arriba no prueban nada."""
    assert MIGRACION == "2026-10-15"
    aceptada(importar(mundo, mundo.torre, padron()))
