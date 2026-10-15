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


def test_existe_un_paso_de_shellcheck_con_version_fijada_sobre_infra() -> None:
    """D19 (cambio 1d): el CI corre `shellcheck`, versión fijada, sobre todos
    los `*.sh` de `infra/`. No es opcional: antes de este cambio no existía
    ningún paso así."""
    texto = WORKFLOW.read_text()
    assert "shellcheck" in texto.lower(), "no hay ningún paso de shellcheck en el workflow"
    # Versión fijada (como gitleaks, D19): un tag o SHA, nunca `latest`/`stable`.
    assert "shellcheck:latest" not in texto
    assert "shellcheck:stable" not in texto
    assert re.search(r"shellcheck:v?[0-9]+\.[0-9]+\.[0-9]+", texto), (
        "el paso de shellcheck no fija una versión concreta"
    )
    assert "infra" in texto.lower()


def test_canario_shellcheck_detecta_variable_sin_comillas() -> None:
    """D19/L-013: una COPIA (nunca el script real) con una variable sin
    comillas hace fallar `shellcheck`, con la misma imagen y versión fijada
    que usa el workflow. Si este canario no fallara, el paso del CI sería
    decorativo."""
    import subprocess
    import tempfile

    script_real = RAIZ / "infra" / "ci" / "test-backend.sh"
    contenido_original = script_real.read_text()

    with tempfile.TemporaryDirectory() as carpeta_temporal:
        copia_rota = Path(carpeta_temporal) / "canario-roto.sh"
        # Variable sin comillas a propósito (SC2086): nunca se toca el script real.
        copia_rota.write_text('#!/usr/bin/env bash\narchivo="mi archivo.txt"\ncat $archivo\n')

        resultado = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{carpeta_temporal}:/mnt",
                "koalaman/shellcheck:v0.11.0",
                "/mnt/canario-roto.sh",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    assert resultado.returncode != 0, (
        "el canario (variable sin comillas) debía hacer fallar a shellcheck"
    )
    assert "SC2086" in resultado.stdout or "SC2086" in resultado.stderr

    # El script real nunca se tocó.
    assert script_real.read_text() == contenido_original
