"""`humo.sh` y `ensayo-roles.sh` se niegan a correr donde podrían borrar el stack real (2e, L-047).

Escenarios de `integracion-continua`: El humo corre sólo en un proyecto de Compose aislado; el
ensayo de roles comparte la comprobación. Los dos hacen `up --build` y `down -v`, así que los dos
rechazan ANTES de ejecutar cualquier `compose`: (a) sin `PROPTECH_COMPOSE_PROYECTO`; (b) con el
valor `proptech`, SIEMPRE (haya o no contenedores corriendo: el stack real detenido conserva sus
volúmenes y un `down -v` se los lleva, hallazgo R1 del rompedor); (c) con el puerto 80 o 443 del
host ocupado. Sin Docker: un `docker` falso en el PATH registra cada invocación.
"""

import os
import shutil
import socket
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
CI = RAIZ / "infra" / "ci"
SCRIPTS = ("humo.sh", "ensayo-roles.sh")

#: `docker` falso: registra cada llamada. Dice que hay contenedores sólo si `STUB_PS_Q` lo indica
#: (corriendo) o `STUB_PS_AQ` (también detenidos). Todo `up` falla: el script baja por su `trap`.
_DOCKER_FALSO = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
if [ "$1" = "ps" ]; then
  case " $* " in
    *" -a"*|*" --all "*) printf '%s' "${STUB_PS_AQ:-}" ;;
    *) printf '%s' "${STUB_PS_Q:-}" ;;
  esac
  exit 0
fi
if [ "$1" = "volume" ]; then
  printf '%s' "${STUB_VOLUMENES:-}"
  exit 0
fi
if [ "$1" = "compose" ]; then
  case " $* " in
    *" up "*) exit 1 ;;
  esac
fi
exit 0
"""


def _puerto_libre() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return int(sonda.getsockname()[1])


@contextmanager
def _puerto_ocupado() -> Iterator[int]:
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen()
        yield servidor.getsockname()[1]


def _correr(
    tmp_path: Path, script: str, *, proyecto: str | None, puertos: str, **stub: str
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    ci = tmp_path / "infra" / "ci"
    ci.mkdir(parents=True)
    for archivo in (script, "pasos.sh", "humo-lib.sh"):
        shutil.copy(CI / archivo, ci / archivo)
    for carpeta in ("backend", "web", ".git"):
        (tmp_path / carpeta).mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(_DOCKER_FALSO)
    docker.chmod(0o755)
    registro = tmp_path / "docker.log"
    registro.write_text("")
    entorno = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "STUB_LOG": str(registro),
        "PROPTECH_HUMO_PUERTOS": puertos,
        **stub,
    }
    if proyecto is not None:
        entorno["PROPTECH_COMPOSE_PROYECTO"] = proyecto
    resultado = subprocess.run(
        ["bash", str(ci / script)],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return resultado, registro.read_text().splitlines()


def _compose(registro: list[str]) -> list[str]:
    return [linea for linea in registro if linea.startswith("compose")]


@pytest.mark.parametrize("script", SCRIPTS)
def test_sin_variable_se_niega_antes_de_tocar_compose(tmp_path: Path, script: str) -> None:
    resultado, registro = _correr(tmp_path, script, proyecto=None, puertos=str(_puerto_libre()))
    assert resultado.returncode != 0
    assert "falta PROPTECH_COMPOSE_PROYECTO" in resultado.stderr
    assert script in resultado.stderr, "el mensaje tiene que decir cómo correr ESTE script"
    assert _compose(registro) == []


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize(
    "stub",
    [
        pytest.param({}, id="sin_ningun_contenedor"),
        pytest.param({"STUB_PS_Q": "a1b2c3"}, id="con_contenedores_corriendo"),
        pytest.param(
            {"STUB_PS_AQ": "c0ffee", "STUB_VOLUMENES": "proptech_datos_postgres"},
            id="stack_real_detenido_con_volumenes",
        ),
    ],
)
def test_con_el_proyecto_proptech_se_niega_siempre(
    tmp_path: Path, script: str, stub: dict[str, str]
) -> None:
    """Cambia lo aprobado antes ("con contenedores corriendo"): `proptech` es el proyecto de uso
    real y se rechaza haya o no contenedores corriendo. Ni un `up` ni un `down -v`."""
    resultado, registro = _correr(
        tmp_path, script, proyecto="proptech", puertos=str(_puerto_libre()), **stub
    )
    assert resultado.returncode != 0
    assert "'proptech'" in resultado.stderr
    assert script in resultado.stderr
    assert _compose(registro) == [], f"se invocó compose sobre proptech: {_compose(registro)}"
    assert [linea for linea in registro if " down" in f" {linea}"] == []


@pytest.mark.parametrize("script", SCRIPTS)
def test_con_el_puerto_ocupado_se_niega_y_nombra_el_puerto(tmp_path: Path, script: str) -> None:
    with _puerto_ocupado() as puerto:
        resultado, registro = _correr(
            tmp_path, script, proyecto="proptech-prueba", puertos=str(puerto)
        )
    assert resultado.returncode != 0
    assert str(puerto) in resultado.stderr
    assert "ocupado" in resultado.stderr
    assert _compose(registro) == []


@pytest.mark.parametrize("script", SCRIPTS)
def test_el_nombre_parecido_a_proptech_pero_distinto_pasa_el_rechazo(
    tmp_path: Path, script: str
) -> None:
    """Sólo el valor exacto `proptech` se rechaza; cualquier otro nombre sigue permitido."""
    _, registro = _correr(
        tmp_path, script, proyecto="proptech-humo-prueba", puertos=str(_puerto_libre())
    )
    llamadas = _compose(registro)
    assert llamadas, "el rechazo previo frenó un proyecto propio"
    assert all(linea.startswith("compose -p proptech-humo-prueba ") for linea in llamadas)


def test_el_ci_usa_proyectos_distintos_de_proptech_en_los_dos_jobs() -> None:
    import yaml

    jobs = yaml.safe_load((RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))[
        "jobs"
    ]
    for job, esperado in (("humo", "proptech-humo"), ("ensayo-roles", "proptech-ensayo")):
        assert jobs[job]["env"]["PROPTECH_COMPOSE_PROYECTO"] == esperado


@pytest.mark.parametrize("script", SCRIPTS)
def test_los_dos_scripts_comparten_la_comprobacion_de_humo_lib(script: str) -> None:
    """Una sola implementación: el script llama a la función de `humo-lib.sh` y no repite el
    rechazo ni el valor `proptech` por su cuenta."""
    texto = (CI / script).read_text(encoding="utf-8")
    assert "exigir_proyecto_de_compose_propio" in texto
    assert ":-proptech" not in texto
    assert "/dev/tcp" not in texto
    lib = (CI / "humo-lib.sh").read_text(encoding="utf-8")
    assert "exigir_proyecto_de_compose_propio()" in lib
