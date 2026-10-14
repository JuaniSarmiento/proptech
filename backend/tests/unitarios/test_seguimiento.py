"""Tests de `validar_request_id` contra la tabla compartida de casos (D8, L-008,
L-009). Cambio 1c, tarea 3.1.

Escenarios de `trazabilidad-y-logs`: UUID con espacios, tabulaciones, saltos de
línea o dígitos no ASCII; UUID en mayúsculas; Número de seguimiento malicioso;
Mismos casos en la web y en la API (lado Python).
"""

import json
from pathlib import Path
from typing import cast

from proptech_core.compartido.seguimiento import validar_request_id

RAIZ = Path(__file__).resolve().parents[3]
TABLA = RAIZ / "config" / "contratos" / "request-id.json"

#: Motivos que la tabla de inválidos tiene que cubrir sí o sí (D8): así nadie
#: la vacía sin que falle este test.
MOTIVOS_OBLIGATORIOS = {
    "vacio",
    "largo_35",
    "largo_37",
    "sin_guiones",
    "llaves",
    "espacio_alrededor",
    "tabulacion_alrededor",
    "salto_de_linea_inicio",
    "salto_de_linea_final",
    "digito_no_ascii",
    "letra_ancho_completo",
    "script",
    "comillas",
    "inyeccion_sql",
}


def _tabla() -> dict[str, list[dict[str, str]]]:
    return cast(dict[str, list[dict[str, str]]], json.loads(TABLA.read_text(encoding="utf-8")))


def test_la_tabla_tiene_al_menos_un_caso_de_cada_motivo_obligatorio() -> None:
    datos = _tabla()
    motivos_presentes = {caso["motivo"] for caso in datos["invalidos"]}
    faltantes = MOTIVOS_OBLIGATORIOS - motivos_presentes
    assert not faltantes, f"faltan casos para los motivos: {faltantes}"


def test_la_tabla_tiene_al_menos_un_valido_en_mayusculas() -> None:
    datos = _tabla()
    motivos_presentes = {caso["motivo"] for caso in datos["validos"]}
    assert "mayusculas" in motivos_presentes


def test_cada_valido_de_la_tabla_se_acepta_y_normaliza() -> None:
    for caso in _tabla()["validos"]:
        resultado = validar_request_id(caso["entrada"])
        assert resultado == caso["normalizado"], caso


def test_cada_invalido_de_la_tabla_se_rechaza() -> None:
    for caso in _tabla()["invalidos"]:
        resultado = validar_request_id(caso["entrada"])
        assert resultado is None, f"debería rechazarse ({caso['motivo']}): {caso!r}"
