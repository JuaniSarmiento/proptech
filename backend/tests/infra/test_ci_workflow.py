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


def test_disparadores_incluyen_push_a_main_workflow_dispatch_y_pull_request() -> None:
    """MODIFIED de 'Verificaciones en cada push' (tarea 4.3): sumar
    `pull_request` sin perder `push: branches: [main]` ni
    `workflow_dispatch` (si `push` perdiera el filtro de rama, correría en
    cualquier push a cualquier rama, no sólo a `main`)."""
    datos = _workflow()
    disparador = datos[True] if True in datos else datos.get("on")
    assert disparador is not None, "no se encontró la clave on:"
    assert "push" in disparador
    ramas = disparador["push"].get("branches") if isinstance(disparador["push"], dict) else None
    assert ramas is None or "main" in ramas
    assert "workflow_dispatch" in disparador
    assert "pull_request" in disparador


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


#: D5 (tarea 4.3): medidos contra `gh run view` del CI real (último push,
#: 2026-10-15 23:32Z): backend 9m08s y con tendencia creciente (4m26s,
#: 5m18s, 5m32s, 9m08s en las cuatro corridas previas); humo 1 a 2 min;
#: shellcheck y secretos, menos de 20s cada uno. `web` subió de 5 a 15
#: (tarea 3.8 del 3b: sumó `next build` + Chromium real sobre vitest, que
#: solo); sin medición real de CI todavía, 15 deja margen sobre lo que se
#: vio en esta máquina (unos 90s de punta a punta). `backend` subió de 20 a
#: 30 el 22/10/2026: la suite pasó a 9-11 min y `canario.sh` la repite entera,
#: así que 20 cortó una corrida verde (run 39783653827). `web` subió de 15 a 25
#: el 26/10/2026: `playwright install --with-deps chromium` tardó 10 min en el
#: runner y el job llegó a 15:40, cortando el canario con los tests ya en verde
#: (run 40357665108, intentos 1 y 2).
_TIMEOUT_MINUTES_ESPERADO = {
    "backend": 30,
    "humo": 15,
    "web": 25,
    "shellcheck": 5,
    "secretos": 5,
}


def test_timeout_minutes_de_cada_trabajo() -> None:
    datos = _workflow()
    jobs = datos.get("jobs", {})
    for nombre, minutos in _TIMEOUT_MINUTES_ESPERADO.items():
        assert nombre in jobs, f"falta el job {nombre}"
        assert jobs[nombre].get("timeout-minutes") == minutos, (
            f"el job {nombre} esperaba timeout-minutes: {minutos}, "
            f"tiene {jobs[nombre].get('timeout-minutes')!r}"
        )


_PATRON_IMAGEN_CON_DIGEST = re.compile(r"[\w./-]+:v?[0-9][0-9.]*@sha256:[0-9a-f]{64}")


def test_gitleaks_y_shellcheck_fijados_por_tag_y_digest() -> None:
    """D19/D5: un tag solo (como ya pasaba con gitleaks) se puede
    re-publicar con otro contenido sin que nadie lo note; `@sha256:` fija
    el contenido exacto. El digest tiene que venir del registro (`docker
    manifest inspect`), no de una copia local que puede estar desalineada
    con lo que el tag apunta hoy (hallazgo real de esta tarea)."""
    texto = WORKFLOW.read_text()
    for imagen in ("zricethezav/gitleaks", "koalaman/shellcheck"):
        coincidencias = [
            m.group(0) for m in _PATRON_IMAGEN_CON_DIGEST.finditer(texto) if imagen in m.group(0)
        ]
        assert coincidencias, f"{imagen} no está fijada con tag Y @sha256: en el workflow"
