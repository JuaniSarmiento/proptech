"""Gemelo de `test_arranque_api_parametros.py` (L-009). Cambio 1c, tarea 5.9.

El worker no arranca con parámetros inválidos ni con `PROPTECH_PARAMETROS`
faltante, vacía o inexistente.
"""

import os
import subprocess
import sys
from pathlib import Path


def test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo(tmp_path: Path) -> None:
    archivo = tmp_path / "parametros.yaml"
    archivo.write_text(
        "version: 1\n"
        'intereses: {tasa_mensual: "-1.00", dias_de_gracia: 0, '
        "forma_de_calculo: proporcional_por_dia}\n"
        'fondo_de_reserva: {porcentaje: "0.00"}\n'
        "categorias_de_gasto: [{clave: varios, nombre: Varios}]\n"
        "grupos_de_reparto: [{clave: generales, nombre: Generales, "
        "metodo: coeficiente, alcance: todas_las_unidades}]\n"
        "tipos_de_unidad: [{clave: departamento, nombre: Departamento}]\n"
        "estados_de_unidad: {habilitados: false, estados: []}\n"
    )

    entorno = dict(os.environ)
    entorno["PROPTECH_PARAMETROS"] = str(archivo)

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0
    assert "intereses.tasa_mensual" in resultado.stderr, resultado.stderr


def test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable() -> None:
    entorno = dict(os.environ)
    entorno.pop("PROPTECH_PARAMETROS", None)

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0
    assert "PROPTECH_PARAMETROS" in resultado.stderr, resultado.stderr


def test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable() -> None:
    entorno = dict(os.environ)
    entorno["PROPTECH_PARAMETROS"] = ""

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0
    assert "PROPTECH_PARAMETROS" in resultado.stderr, resultado.stderr


def test_el_proceso_termina_con_proptech_parametros_inexistente_nombrando_la_variable() -> None:
    entorno = dict(os.environ)
    entorno["PROPTECH_PARAMETROS"] = "/no/existe/parametros.yaml"

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0
    assert "PROPTECH_PARAMETROS" in resultado.stderr, resultado.stderr
