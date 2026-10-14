"""El pin de PyYAML exige una versión con wheel para Python 3.14 (D5, cambio 1c, 1.3)."""

import re
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def test_pyproject_exige_pyyaml_6_0_3_o_mas() -> None:
    datos = tomllib.loads((RAIZ / "backend" / "pyproject.toml").read_text())
    dependencias = datos["project"]["dependencies"]
    especificador = next((d for d in dependencias if d.startswith("pyyaml")), None)
    assert especificador is not None, "no se encontró la dependencia pyyaml en pyproject.toml"

    coincidencia = re.search(r">=\s*(\d+)\.(\d+)\.(\d+)", especificador)
    assert coincidencia is not None, f"pyproject.toml no fija un mínimo >=X.Y.Z: {especificador}"
    minimo = tuple(int(parte) for parte in coincidencia.groups())
    assert minimo >= (6, 0, 3), (
        f"pyproject.toml pide pyyaml {especificador}, necesita >=6.0.3 "
        "(no hay wheel de 6.0.2 para Python 3.14 en Windows)"
    )


def test_uv_lock_resuelve_pyyaml_6_0_3_o_mas() -> None:
    contenido = (RAIZ / "backend" / "uv.lock").read_text()
    coincidencia = re.search(r'name = "pyyaml"\nversion = "(\d+)\.(\d+)\.(\d+)"', contenido)
    assert coincidencia is not None, "no se encontró el paquete pyyaml en uv.lock"
    version = tuple(int(parte) for parte in coincidencia.groups())
    assert version >= (6, 0, 3), f"uv.lock resuelve pyyaml {version}, necesita >=6.0.3"


# --- 4.2: dependencias de la cola (D1) ---


def _dependencias_pyproject() -> list[str]:
    datos = tomllib.loads((RAIZ / "backend" / "pyproject.toml").read_text())
    dependencias: list[str] = list(datos["project"]["dependencies"])
    return dependencias


def test_pyproject_exige_arq_0_28_0() -> None:
    dependencias = _dependencias_pyproject()
    assert "arq==0.28.0" in dependencias, dependencias


def test_pyproject_exige_redis_hiredis_mayor_igual_5_3_1_menor_6() -> None:
    dependencias = _dependencias_pyproject()
    especificador = next((d for d in dependencias if d.startswith("redis")), None)
    assert especificador is not None, f"no se encontró la dependencia redis en {dependencias}"
    assert "hiredis" in especificador, especificador
    assert ">=5.3.1" in especificador.replace(" ", ""), especificador
    assert "<6" in especificador.replace(" ", ""), especificador


def test_pyproject_prohibe_testcontainers_redis() -> None:
    """D1: testcontainers[redis] exige redis>=7 (Python) y choca con el <6 de
    ARQ; Redis en los tests se levanta con DockerContainer genérico."""
    texto = (RAIZ / "backend" / "pyproject.toml").read_text()
    assert "testcontainers[redis]" not in texto, texto


def test_uv_lock_resuelve_arq_0_28_0() -> None:
    contenido = (RAIZ / "backend" / "uv.lock").read_text()
    assert re.search(r'name = "arq"\nversion = "0\.28\.0"', contenido), (
        "uv.lock no resuelve arq en 0.28.0"
    )


def test_uv_lock_resuelve_redis_en_rama_5() -> None:
    contenido = (RAIZ / "backend" / "uv.lock").read_text()
    coincidencia = re.search(r'name = "redis"\nversion = "(\d+)\.(\d+)\.(\d+)"', contenido)
    assert coincidencia is not None, "no se encontró el paquete redis en uv.lock"
    version = tuple(int(parte) for parte in coincidencia.groups())
    assert (5, 3, 1) <= version < (6, 0, 0), (
        f"uv.lock resuelve redis {version}, necesita >=5.3.1,<6"
    )
