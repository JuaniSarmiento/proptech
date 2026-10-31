"""Los ids de los tests no dependen de la hora ni del proceso (cambio 2e `humo-y-ci`, xdist).

`pytest-xdist` colecciona la suite en cada trabajador y aborta con "Different tests were
collected" si los ids no coinciden. Un parámetro calculado con la hora actual
(`test_falla_con_marca_en_el_futuro`) cambiaba de id cada segundo: el paralelo fallaba de forma
intermitente, una corrida de cada varias.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def _coleccionar(semilla_de_hash: str) -> list[str]:
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-m",
            "not integracion",
            "tests/infra/test_respaldos.py",
            "tests/unitarios/test_logs.py",
        ],
        cwd=BACKEND,
        env={**os.environ, "PYTHONHASHSEED": semilla_de_hash},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert resultado.returncode == 0, resultado.stdout[-800:] + resultado.stderr[-800:]
    return [linea for linea in resultado.stdout.splitlines() if "::" in linea]


def test_los_ids_no_cambian_con_el_reloj_ni_con_la_semilla_de_hash() -> None:
    primera = _coleccionar("1")
    time.sleep(1.2)
    segunda = _coleccionar("2")
    assert primera, "no se coleccionó ningún test"
    assert primera == segunda
