"""Tests estáticos sobre .github/workflows/ci.yml (D6)."""

import re
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
WORKFLOW = RAIZ / ".github" / "workflows" / "ci.yml"

PATRON_SHA_40 = re.compile(r"@[0-9a-f]{40}$")


def _workflow() -> dict[Any, Any]:
    # El YAML de GitHub Actions usa la clave reservada "on", que PyYAML
    # interpreta como booleano `True`; se carga igual y se la busca por
    # su valor real en vez de la cadena "on".
    datos = yaml.safe_load(WORKFLOW.read_text())
    assert isinstance(datos, dict)
    return datos


def _todos_los_uses(datos: dict[Any, Any]) -> list[str]:
    usados = []
    for job in datos.get("jobs", {}).values():
        for paso in job.get("steps", []):
            if "uses" in paso:
                usados.append(paso["uses"])
    return usados


def test_workflow_existe() -> None:
    assert WORKFLOW.exists(), "falta .github/workflows/ci.yml"


def test_jobs_esperados_existen() -> None:
    datos = _workflow()
    jobs = set(datos.get("jobs", {}))
    for esperado in ("backend", "web", "humo", "secretos"):
        assert esperado in jobs, f"falta el job {esperado}"


def test_cada_uses_esta_fijado_a_un_sha_de_40_caracteres() -> None:
    datos = _workflow()
    usos = _todos_los_uses(datos)
    assert usos, "no se encontró ningún `uses:` en el workflow"
    for uso in usos:
        assert PATRON_SHA_40.search(uso), f"{uso} no está fijado a un SHA de 40 caracteres"


def test_no_hay_continue_on_error_ni_or_true() -> None:
    texto = WORKFLOW.read_text()
    assert "continue-on-error" not in texto
    assert "|| true" not in texto


def test_disparadores_incluyen_push_a_main_y_workflow_dispatch() -> None:
    datos = _workflow()
    disparador = datos[True] if True in datos else datos.get("on")
    assert disparador is not None, "no se encontró la clave on:"
    assert "push" in disparador
    ramas = disparador["push"].get("branches") if isinstance(disparador["push"], dict) else None
    assert ramas is None or "main" in ramas
    assert "workflow_dispatch" in disparador


def test_permisos_son_solo_contents_read() -> None:
    datos = _workflow()
    assert datos.get("permissions") == {"contents": "read"}


def test_pasos_de_test_llaman_a_los_scripts_unicos() -> None:
    texto = WORKFLOW.read_text()
    assert "infra/ci/test-backend.sh" in texto
    assert "infra/ci/test-web.sh" in texto


def test_existen_los_pasos_del_canario() -> None:
    texto = WORKFLOW.read_text()
    assert "infra/ci/canario.sh backend" in texto
    assert "infra/ci/canario.sh web" in texto
