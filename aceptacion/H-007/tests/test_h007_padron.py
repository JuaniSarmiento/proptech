"""H-007 · C01 a C08 (backend): lo que tiene que pasar al importar el padrón desde la plantilla."""

from __future__ import annotations

import io
import re
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from ._h007 import (
    ARCHIVO,
    ENCABEZADOS,
    XLSX,
    Mundo,
    aceptada,
    auditorias,
    con_formula,
    conteos,
    fila_del_excel,
    filas_validas,
    importar,
    libro,
    padron,
    propietarios,
    unidades,
)

pytestmark = pytest.mark.integracion


# --- C01 · Archivo válido -------------------------------------------------------------------------


def test_c01_doce_unidades_validas(mundo: Mundo) -> None:
    """Escenario: Doce unidades con propietarios"""
    cuerpo = aceptada(importar(mundo, mundo.torre, padron()))
    creadas = unidades(mundo, mundo.torre)
    esperadas = {
        f["Unidad"]: {
            "tipo": f["Tipo"],
            "piso": f["Piso"],
            "coeficiente": f["Coeficiente"],
            "superficie": f["Superficie m2"],
        }
        for f in filas_validas()
    }
    assert creadas == esperadas, f"el padrón no quedó como el archivo: {creadas}"
    assert cuerpo["unidades_creadas"] == 12
    # Todas en el grupo general, con el informe de R01 en "ok" (suman 1 exacto).
    grupos = mundo.cliente.get(f"/api/complejos/{mundo.torre}/grupos")
    assert grupos.status_code == 200, grupos.text
    generales = next(g for g in grupos.json() if g["es_generales"])
    assert len(generales["unidades"]) == 12
    assert generales["informe"]["estado"] == "ok", generales["informe"]
    # Una auditoría de alta por unidad (como el alta manual) y la de la importación.
    assert auditorias(mundo, "crear_unidad") == 12
    assert auditorias(mundo, "importar_padron_y_saldos") == 1


def test_c01_la_importacion_queda_registrada(mundo: Mundo) -> None:
    """La subida aceptada queda en `importacion` con su huella y la fecha de migración."""
    cuerpo = aceptada(importar(mundo, mundo.torre, padron()))
    filas = mundo.filas(
        "SELECT complejo_id, fecha_de_migracion::text, length(huella) FROM importacion "
        "WHERE id = %s",
        (cuerpo["importacion_id"],),
    )
    assert filas == [(mundo.torre, "2026-10-15", 64)], filas


# --- C02 · Columnas en cualquier orden ------------------------------------------------------------


def test_c02_columnas_en_otro_orden(mundo: Mundo) -> None:
    """Escenario: Columnas en otro orden"""
    orden = ["Email", "Piso", "Unidad", "Superficie m2", "Tipo", "Coeficiente", "Propietario"]
    aceptada(importar(mundo, mundo.torre, padron(encabezados=orden)))
    assert len(unidades(mundo, mundo.torre)) == 12
    assert unidades(mundo, mundo.torre)["2B"] == {
        "tipo": "departamento",
        "piso": "2",
        "coeficiente": "0.083333",
        "superficie": "52.25",
    }


def test_c02_columnas_extra_se_ignoran(mundo: Mundo) -> None:
    encabezados = ["Observaciones", *ENCABEZADOS, "Teléfono"]
    filas = [{**f, "Observaciones": "nota", "Teléfono": "261 000 0000"} for f in filas_validas()]
    aceptada(importar(mundo, mundo.torre, padron(filas, encabezados=encabezados)))
    assert len(unidades(mundo, mundo.torre)) == 12


# --- C03 · Propietarios sin invitar ---------------------------------------------------------------


def test_c03_diez_propietarios_sin_invitacion(mundo: Mundo) -> None:
    """Escenario: Doce unidades con propietarios"""
    antes = conteos(mundo)
    aceptada(importar(mundo, mundo.torre, padron()))
    duenos = propietarios(mundo, mundo.torre)
    assert len(duenos) == 10
    assert duenos["2B"] == ("Persona Ficticia 3", "propietario3@ficticio.test")
    despues = conteos(mundo)
    assert despues["persona"] - antes["persona"] == 10
    assert despues["asignacion_vecino"] - antes["asignacion_vecino"] == 10
    assert despues["invitacion"] == antes["invitacion"], "importar no invita (E3)"


def test_c03_propietario_sin_email(mundo: Mundo) -> None:
    """Escenario: Propietario sin email"""
    filas = filas_validas()
    filas[0]["Propietario"], filas[0]["Email"] = "Persona Ficticia Uno", None
    aceptada(importar(mundo, mundo.torre, padron(filas)))
    assert propietarios(mundo, mundo.torre)["1A"] == ("Persona Ficticia Uno", None)


def test_c03_mismo_email_en_dos_filas_es_una_persona(mundo: Mundo) -> None:
    filas = filas_validas()
    filas[1]["Email"] = filas[0]["Email"]
    filas[1]["Propietario"] = filas[0]["Propietario"]
    antes = conteos(mundo)
    aceptada(importar(mundo, mundo.torre, padron(filas)))
    duenos = propietarios(mundo, mundo.torre)
    assert duenos["1A"] == duenos["1B"] == ("Persona Ficticia 1", "propietario1@ficticio.test")
    assert conteos(mundo)["persona"] - antes["persona"] == 9


def test_c03_email_existente_reusa_la_persona(mundo: Mundo) -> None:
    mundo.filas(
        "INSERT INTO persona (administracion_id, nombre, email) "
        "VALUES (%s, 'Persona Ficticia Existente', 'existente@ficticio.test') RETURNING id",
        (mundo.admin,),
    )
    filas = filas_validas()
    filas[0]["Email"] = "existente@ficticio.test"
    antes = conteos(mundo)
    aceptada(importar(mundo, mundo.torre, padron(filas)))
    assert propietarios(mundo, mundo.torre)["1A"][1] == "existente@ficticio.test"
    assert mundo.uno("SELECT count(*) FROM persona WHERE email = 'existente@ficticio.test'") == 1
    assert conteos(mundo)["persona"] - antes["persona"] == 9


# --- C04 · Números --------------------------------------------------------------------------------


def test_c04_coma_decimal_punto_y_celda_numerica(mundo: Mundo) -> None:
    """Escenario: Coma decimal"""
    filas = filas_validas()
    filas[0]["Coeficiente"] = "0,083333"
    filas[1]["Coeficiente"] = "0.083333"
    filas[2]["Coeficiente"] = 0.083333  # celda numérica
    aceptada(importar(mundo, mundo.torre, padron(filas)))
    creadas = unidades(mundo, mundo.torre)
    assert creadas["1A"]["coeficiente"] == creadas["1B"]["coeficiente"] == "0.083333"
    assert creadas["2B"]["coeficiente"] == "0.083333"


def test_c04_notacion_cientifica_de_una_celda_numerica(mundo: Mundo) -> None:
    filas = filas_validas()
    filas[11]["Coeficiente"] = 8.3e-05  # celda numérica: se escribe "8.3e-05" en el XML
    filas[10]["Coeficiente"] = "0.166587"  # para que la suma siga en 1
    aceptada(importar(mundo, mundo.torre, padron(filas)))
    assert unidades(mundo, mundo.torre)["C2"]["coeficiente"] == "0.000083"


def test_c04_superficie_con_coma_y_con_punto(mundo: Mundo) -> None:
    filas = filas_validas()
    filas[0]["Superficie m2"] = "45,5"
    filas[1]["Superficie m2"] = "45.50"
    filas[2]["Superficie m2"] = 45.5  # celda numérica
    aceptada(importar(mundo, mundo.torre, padron(filas)))
    creadas = unidades(mundo, mundo.torre)
    assert {creadas[u]["superficie"] for u in ("1A", "1B", "2B")} == {"45.50"}


def test_c04_formula_con_valor_en_cache(mundo: Mundo) -> None:
    filas = filas_validas()
    filas[1]["Superficie m2"] = 999  # celda numérica que se reemplaza por la fórmula
    columna = "ABCDEFG"[ENCABEZADOS.index("Superficie m2")]
    contenido = con_formula(padron(filas), f"{columna}{fila_del_excel('1B')}", "40+5", "45")
    aceptada(importar(mundo, mundo.torre, contenido))
    assert Decimal(unidades(mundo, mundo.torre)["1B"]["superficie"]) == Decimal("45")


# --- C05 · Tolerancia de R01 ----------------------------------------------------------------------


@pytest.mark.parametrize(("ultimo", "texto"), [("0.083237", "0,9999"), ("0.083437", "1,0001")])
def test_c05_suma_dentro_de_la_tolerancia_carga_con_advertencia(
    mundo: Mundo, ultimo: str, texto: str
) -> None:
    """Escenario: Suma 0,9999"""
    filas = filas_validas()
    filas[11]["Coeficiente"] = ultimo
    cuerpo = aceptada(importar(mundo, mundo.torre, padron(filas)))
    assert len(unidades(mundo, mundo.torre)) == 12
    motivos = [
        str(a.get("motivo", a)) if isinstance(a, dict) else str(a) for a in cuerpo["advertencias"]
    ]
    numero = texto.replace(",", "[.,]")
    assert any(re.search(numero, m) for m in motivos), (
        f"falta la advertencia de la suma {texto}: {cuerpo['advertencias']}"
    )


def test_c05_suma_exacta_sin_advertencia(mundo: Mundo) -> None:
    cuerpo = aceptada(importar(mundo, mundo.torre, padron()))
    assert cuerpo["advertencias"] == []


# --- C06 · Edificio con padrón: sin hoja Unidades o con la hoja vacía -----------------------------


@pytest.mark.parametrize("forma", ["sin_hoja", "hoja_vacia"])
def test_c06_edificio_con_unidades_acepta_un_archivo_sin_padron(mundo: Mundo, forma: str) -> None:
    contenido = libro({"Notas": [["Texto"], ["sin padrón"]]}) if forma == "sin_hoja" else padron([])
    antes = unidades(mundo, mundo.con_padron)
    cuerpo = aceptada(importar(mundo, mundo.con_padron, contenido))
    assert cuerpo["unidades_creadas"] == 0
    assert unidades(mundo, mundo.con_padron) == antes, "el padrón existente no se toca"


# --- C07 · El resumen -----------------------------------------------------------------------------


def test_c07_el_resumen_cuenta_unidades_y_propietarios(mundo: Mundo) -> None:
    mundo.filas(
        "INSERT INTO persona (administracion_id, nombre, email) "
        "VALUES (%s, 'Persona Ficticia Existente', 'existente@ficticio.test') RETURNING id",
        (mundo.admin,),
    )
    filas = filas_validas()
    filas[8]["Email"] = filas[0]["Email"]  # misma persona que la fila de 1A: no cuenta como reusada
    filas[8]["Propietario"] = filas[0]["Propietario"]
    filas[9]["Email"] = "existente@ficticio.test"  # ya estaba en la administración: reusada
    cuerpo = aceptada(importar(mundo, mundo.torre, padron(filas)))
    assert cuerpo["unidades_creadas"] == 12
    assert cuerpo["propietarios_creados"] == 8
    assert cuerpo["propietarios_reusados"] == 1
    assert cuerpo["filas_de_saldo"] == 0
    assert cuerpo["advertencias"] == []


# --- C08 · La plantilla (backend de la descarga) --------------------------------------------------


def test_c08_la_plantilla_trae_las_tres_hojas_con_sus_encabezados(mundo: Mundo) -> None:
    respuesta = mundo.cliente.get(f"/api/complejos/{mundo.torre}/importaciones/plantilla")
    assert respuesta.status_code == 200, f"la plantilla no se descarga: {respuesta.status_code}"
    assert respuesta.headers.get("content-type", "").startswith(XLSX), respuesta.headers
    wb = load_workbook(io.BytesIO(respuesta.content), read_only=True)
    encabezados = {
        nombre: [c for c in next(wb[nombre].iter_rows(max_row=1, values_only=True)) if c]
        for nombre in wb.sheetnames
    }
    assert encabezados.get("Unidades") == ENCABEZADOS, encabezados
    assert encabezados.get("Saldos") == [
        "Unidad",
        "Período",
        "Vencimiento",
        "Concepto",
        "Importe",
        "Interés acumulado",
    ], encabezados
    assert encabezados.get("Control") == ["Unidad", "Saldo según el administrador"], encabezados


def test_c08_la_plantilla_descargada_se_puede_completar_e_importar(mundo: Mundo) -> None:
    """La plantilla vacía, completada con las 12 unidades, se importa (el archivo es el nuestro)."""
    respuesta = mundo.cliente.get(f"/api/complejos/{mundo.torre}/importaciones/plantilla")
    assert respuesta.status_code == 200, f"la plantilla no se descarga: {respuesta.status_code}"
    wb = load_workbook(io.BytesIO(respuesta.content))
    hoja = wb["Unidades"]
    encabezados = [str(c.value) for c in hoja[1]]
    for fila in filas_validas():
        hoja.append([fila.get(c) for c in encabezados])
    salida = io.BytesIO()
    wb.save(salida)
    cuerpo = aceptada(importar(mundo, mundo.torre, salida.getvalue(), nombre=ARCHIVO))
    assert cuerpo["unidades_creadas"] == 12
