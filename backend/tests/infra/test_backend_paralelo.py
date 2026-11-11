"""El backend corre en paralelo con `pytest-xdist` sin compartir base (cambio 2e `humo-y-ci`).

Escenarios de `integracion-continua`: Mismos tests, menos tiempo; Aislamiento entre trabajadores;
Un test no tolera el paralelo. D11 del diseño. Lo que depende de Docker y de tiempos (que den los
mismos tests pasados y menos duración) no se prueba acá: se midió en WSL y está en `tasks.md` 9.3.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
BACKEND = RAIZ / "backend"
WORKFLOW = RAIZ / ".github" / "workflows" / "ci.yml"


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))


def test_pytest_xdist_esta_fijado_en_el_grupo_de_desarrollo_y_en_el_lock() -> None:
    desarrollo = _pyproject()["dependency-groups"]["dev"]
    fijadas = [d for d in desarrollo if d.startswith("pytest-xdist")]
    assert len(fijadas) == 1 and re.fullmatch(r"pytest-xdist==\d+\.\d+\.\d+", fijadas[0])
    bloqueo = (BACKEND / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "pytest-xdist"' in bloqueo


def test_el_marcador_serial_esta_registrado() -> None:
    marcadores = _pyproject()["tool"]["pytest"]["ini_options"]["markers"]
    assert any(m.startswith("serial") for m in marcadores)


def test_todo_test_serial_dice_su_motivo() -> None:
    """Un test que sólo es correcto en serie se marca con un motivo escrito, nunca se saca de la
    suite (spec: "Un test no tolera el paralelo")."""
    sin_motivo = []
    for archivo in (BACKEND / "tests").rglob("*.py"):
        if archivo == Path(__file__):
            continue
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if "pytest.mark.serial" in linea and not linea.lstrip().startswith("#"):
                if "reason=" not in linea:
                    sin_motivo.append(f"{archivo.relative_to(RAIZ)}:{numero}")
    assert sin_motivo == [], f"marcador serial sin reason=: {sin_motivo}"


def _pasos_del_backend() -> list[dict[str, Any]]:
    datos = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return list(datos["jobs"]["backend"]["steps"])


def _comandos_de_test() -> list[str]:
    return [p["run"] for p in _pasos_del_backend() if "test-backend.sh" in p.get("run", "")]


def test_el_job_backend_separa_unitarios_de_integracion() -> None:
    comandos = _comandos_de_test()
    assert any('-m "not integracion' in c for c in comandos), "falta el paso de unitarios"
    assert any('-m "integracion' in c for c in comandos), "falta el paso de integración"


def test_los_pasos_paralelos_usan_un_numero_fijo_de_workers_nunca_auto() -> None:
    paralelos = [c for c in _comandos_de_test() if " -n " in c]
    assert paralelos, "ningún paso del backend usa -n"
    for comando in paralelos:
        assert re.search(r" -n [1-9][0-9]*(\s|$)", comando), comando
        assert "auto" not in comando


def test_los_pasos_paralelos_excluyen_los_tests_serial() -> None:
    for comando in _comandos_de_test():
        if " -n " in comando:
            assert "not serial" in comando, f"un paso paralelo no incluye la exclusión: {comando}"


def _hay_tests_serial() -> bool:
    for archivo in (BACKEND / "tests").rglob("*.py"):
        if archivo == Path(__file__):
            continue
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "pytest.mark.serial" in linea and not linea.lstrip().startswith("#"):
                return True
    return False


def test_si_hay_tests_serial_corren_aparte_sin_xdist() -> None:
    """Hoy ninguno lo necesita (medido en 9.3). Si alguien marca uno, el CI tiene que correrlo en un
    paso propio con `-p no:xdist`: excluirlo del paralelo sin correrlo en otro lado lo saca de la
    suite."""
    if not _hay_tests_serial():
        return
    aparte = [c for c in _comandos_de_test() if "-m serial" in c or '-m "serial' in c]
    assert aparte, "hay tests serial y ningún paso del CI los corre"
    assert all("-p no:xdist" in c for c in aparte)
