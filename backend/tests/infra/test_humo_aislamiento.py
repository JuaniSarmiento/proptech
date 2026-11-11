"""`humo.sh` corre sólo en un proyecto de Compose aislado (cambio 2e `humo-y-ci`, L-047).

Escenarios de `integracion-continua`: El humo corre sólo en un proyecto de Compose aislado.
Se prueba sin Docker: un `docker` falso en el PATH registra cada invocación, y el humo corre sobre
una copia de `infra/` en `tmp_path` (así sus archivos señuelo `../backend/.env` no tocan el repo).
"""

import os
import re
import shutil
import socket
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
HUMO = RAIZ / "infra" / "ci" / "humo.sh"

_DOCKER_FALSO = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
if [ "$1" = "ps" ]; then
  printf '%s' "${STUB_PS_Q:-}"
  exit 0
fi
if [ "$1" = "compose" ]; then
  case " $* " in
    *" up "*) exit 1 ;;
  esac
fi
exit 0
"""


def _lineas_no_comentario(texto: str) -> list[str]:
    return [linea for linea in texto.splitlines() if not linea.strip().startswith("#")]


def _montar(tmp_path: Path, humo: Path = HUMO) -> Path:
    """Copia `infra/ci/{humo,pasos}.sh` a `tmp_path/infra/ci` y deja un `docker` falso."""
    ci = tmp_path / "infra" / "ci"
    ci.mkdir(parents=True)
    shutil.copy(humo, ci / "humo.sh")
    shutil.copy(RAIZ / "infra" / "ci" / "pasos.sh", ci / "pasos.sh")
    shutil.copy(RAIZ / "infra" / "ci" / "humo-lib.sh", ci / "humo-lib.sh")
    (tmp_path / "backend").mkdir()
    (tmp_path / "web").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(_DOCKER_FALSO)
    docker.chmod(0o755)
    return ci / "humo.sh"


def _correr(
    tmp_path: Path,
    *,
    proyecto: str | None,
    puertos: str,
    contenedores: str = "",
    humo: Path = HUMO,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    script = _montar(tmp_path, humo)
    registro = tmp_path / "docker.log"
    registro.write_text("")
    entorno = {
        "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "STUB_LOG": str(registro),
        "STUB_PS_Q": contenedores,
        "PROPTECH_HUMO_PUERTOS": puertos,
    }
    if proyecto is not None:
        entorno["PROPTECH_COMPOSE_PROYECTO"] = proyecto
    resultado = subprocess.run(
        ["bash", str(script)],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return resultado, registro.read_text().splitlines()


@contextmanager
def _puerto_ocupado() -> Iterator[int]:
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen()
        yield servidor.getsockname()[1]


def _puerto_libre() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return int(sonda.getsockname()[1])


def _llamadas_a_compose(registro: list[str]) -> list[str]:
    return [linea for linea in registro if linea.startswith("compose")]


def test_el_humo_no_lleva_un_nombre_de_proyecto_fijo() -> None:
    """L-047: ni `-p proptech` ni ningún `-p <literal>`; todo `docker compose` usa la variable."""
    texto = HUMO.read_text(encoding="utf-8")
    for linea in _lineas_no_comentario(texto):
        if re.search(r"docker compose\b", linea):
            assert "-p proptech" not in linea, f"nombre de proyecto fijo: {linea.strip()!r}"
            assert re.search(r'-p "?\$\{?PROPTECH_COMPOSE_PROYECTO\}?"?', linea), (
                f"'docker compose' sin el proyecto de la variable: {linea.strip()!r}"
            )


def test_el_humo_exporta_la_variable_antes_de_llamar_a_restaurar() -> None:
    """Error real de `humo.sh:741`: `restaurar.sh` usa `proptech` por defecto, así que sin
    exportar la variable un humo en un proyecto propio habría restaurado contra `proptech`."""
    texto = HUMO.read_text(encoding="utf-8")
    exportada = re.search(r"^export PROPTECH_COMPOSE_PROYECTO\b", texto, flags=re.MULTILINE)
    assert exportada is not None, "el humo no exporta PROPTECH_COMPOSE_PROYECTO"
    restaurar = texto.index("bash respaldos/restaurar.sh")
    assert exportada.start() < restaurar


def test_sin_variable_el_humo_se_niega_antes_de_tocar_docker_compose(tmp_path: Path) -> None:
    resultado, registro = _correr(tmp_path, proyecto=None, puertos=str(_puerto_libre()))
    assert resultado.returncode != 0
    assert "PROPTECH_COMPOSE_PROYECTO" in resultado.stderr
    assert "falta" in resultado.stderr
    assert _llamadas_a_compose(registro) == []


def test_con_proptech_el_humo_se_niega_con_o_sin_contenedores(tmp_path: Path) -> None:
    """Desde la decisión D15 el rechazo no depende de los contenedores; el detalle por caso (sin
    contenedores, corriendo, detenido) está en `test_rechazos_de_scripts_destructivos.py`."""
    resultado, registro = _correr(
        tmp_path, proyecto="proptech", puertos=str(_puerto_libre()), contenedores="a1b2c3"
    )
    assert resultado.returncode != 0
    assert "'proptech'" in resultado.stderr
    assert _llamadas_a_compose(registro) == []


def test_con_el_puerto_ocupado_el_humo_se_niega_y_nombra_el_puerto(tmp_path: Path) -> None:
    with _puerto_ocupado() as puerto:
        resultado, registro = _correr(
            tmp_path, proyecto="proptech-humo-prueba", puertos=str(puerto)
        )
    assert resultado.returncode != 0
    assert str(puerto) in resultado.stderr
    assert "ocupado" in resultado.stderr
    assert _llamadas_a_compose(registro) == []


def test_con_proyecto_propio_y_host_libre_todo_compose_usa_ese_proyecto(tmp_path: Path) -> None:
    """El `docker` falso hace fallar el primer `up`: el humo llega hasta ahí (el rechazo previo no
    lo frena) y cada llamada a Compose, la de la limpieza incluida, lleva el proyecto de la
    variable."""
    resultado, registro = _correr(
        tmp_path, proyecto="proptech-humo-prueba", puertos=str(_puerto_libre())
    )
    assert resultado.returncode != 0
    llamadas = _llamadas_a_compose(registro)
    assert any(" up " in f" {linea} " for linea in llamadas), "el humo no llegó al primer up"
    assert llamadas
    for linea in llamadas:
        assert linea.startswith("compose -p proptech-humo-prueba "), linea
