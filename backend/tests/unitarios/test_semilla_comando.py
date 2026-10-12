"""5.3: `python -m proptech_core.compartido.semilla <ruta>` (D10)."""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PARAMETROS = RAIZ / "config" / "parametros.yaml"
SEMILLA_VALIDA = RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"


def _entorno_sin_postgres() -> dict[str, str]:
    entorno = {
        clave: valor for clave, valor in os.environ.items() if not clave.startswith("POSTGRES_")
    }
    entorno["PROPTECH_PARAMETROS"] = str(PARAMETROS)
    return entorno


def test_semilla_valida_termina_con_codigo_0_sin_variables_de_postgres() -> None:
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.semilla", str(SEMILLA_VALIDA)],
        env=_entorno_sin_postgres(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_semilla_invalida_termina_con_codigo_1_mostrando_errores(tmp_path: Path) -> None:
    ruta = tmp_path / "invalida.yaml"
    ruta.write_text(
        "version: 1\nedificio: {nombre: '', localidad: Mendoza}\nunidades: []\ngrupos: {}\n"
    )

    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.semilla", str(ruta)],
        env=_entorno_sin_postgres(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert resultado.returncode == 1
    assert resultado.stderr.strip() != ""


def test_semilla_con_clave_no_texto_termina_con_codigo_1_sin_traceback(tmp_path: Path) -> None:
    """L-009 (constructor, cambio 1b vuelta 4): antes del arreglo en
    `cargar_yaml`, una clave no-texto en la raíz escapaba como `TypeError`
    crudo hasta este comando: traceback en stderr en vez de un
    `SemillaInvalida` prolijo (y, de paso, el contenido del archivo
    expuesto en la traza)."""
    ruta = tmp_path / "clave_no_texto.yaml"
    ruta.write_text("1: SECRETO-XYZ\nversion: 1\n")

    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.semilla", str(ruta)],
        env=_entorno_sin_postgres(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stderr
    assert "SECRETO-XYZ" not in resultado.stderr
