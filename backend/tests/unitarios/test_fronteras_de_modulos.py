"""Fronteras entre módulos (D-021, design.md "Fronteras", cambio 2a, tarea
5.1): `compartido` no importa `acceso`, y `acceso` no importa `complejos`.
Recorre los imports con `ast`, nunca ejecutando el código de `proptech_core`.
"""

import ast
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

RAIZ_SRC = Path(__file__).resolve().parents[2] / "src" / "proptech_core"


def _imports_de(archivo: Path) -> list[tuple[int, str | None]]:
    """Cada import del archivo, como `(level, module)`: `level` es la
    cantidad de puntos de un import relativo (0 para uno absoluto)."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    resultado: list[tuple[int, str | None]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                resultado.append((0, alias.name))
        elif isinstance(nodo, ast.ImportFrom):
            resultado.append((nodo.level, nodo.module))
            if nodo.module in (None, "proptech_core"):
                for alias in nodo.names:
                    prefijo = f"{nodo.module}." if nodo.module else ""
                    resultado.append((nodo.level, prefijo + alias.name))
    return resultado


def _primer_segmento_relevante(level: int, module: str | None) -> str | None:
    """A qué paquete de `proptech_core` apunta un import, sea absoluto
    (`proptech_core.acceso...` o `proptech_core.acceso`) o relativo dentro
    del propio `proptech_core` (`from .. import acceso`, `from ..acceso
    import x`, con `level` >= 1): el nombre del paquete hermano, o `None` si
    el import no apunta a ninguno (p. ej. una librería externa)."""
    if module is None:
        return None
    partes = module.split(".")
    if level == 0:
        if "proptech_core" in partes:
            i = partes.index("proptech_core")
            return partes[i + 1] if len(partes) > i + 1 else None
        return None
    # Relativo: `level` puntos desde el archivo. Dentro de proptech_core,
    # un import con level >= 1 cuyo primer segmento no es el propio paquete
    # del archivo apunta a un paquete hermano (p. ej. desde
    # `compartido/x.py`, `from ..acceso import y` tiene level=2, module="acceso").
    return partes[0] if partes and partes[0] else None


def _archivos_que_importan(paquete_origen: str, paquete_objetivo: str) -> list[str]:
    base = RAIZ_SRC / paquete_origen
    ofensores: list[str] = []
    if not base.is_dir():
        return ofensores
    for archivo in sorted(base.rglob("*.py")):
        for level, module in _imports_de(archivo):
            if _primer_segmento_relevante(level, module) == paquete_objetivo:
                ofensores.append(str(archivo.relative_to(RAIZ_SRC.parent)))
                break
    return ofensores


def test_compartido_no_importa_acceso() -> None:
    ofensores = _archivos_que_importan("compartido", "acceso")
    assert ofensores == [], f"compartido no puede importar acceso: {ofensores}"


def test_acceso_no_importa_complejos() -> None:
    ofensores = _archivos_que_importan("acceso", "complejos")
    assert ofensores == [], f"acceso no puede importar complejos: {ofensores}"


# --- Rojo real (L-013): una copia con el import agregado a propósito ---


@pytest.fixture
def copia_de_compartido() -> Iterator[Path]:
    """Copia real de `compartido/` en una carpeta temporal (no el árbol del
    repo): el checker recibe esta ruta en vez de `RAIZ_SRC`, así la mutación
    no toca ni un byte del código real."""
    import shutil

    with tempfile.TemporaryDirectory() as carpeta:
        destino = Path(carpeta) / "compartido"
        shutil.copytree(RAIZ_SRC / "compartido", destino)
        yield destino


def test_el_checker_encuentra_un_import_de_acceso_agregado_a_una_copia(
    copia_de_compartido: Path,
) -> None:
    archivo_mutado = copia_de_compartido / "base_de_datos.py"
    texto_original = archivo_mutado.read_text(encoding="utf-8")
    assert "proptech_core.acceso" not in texto_original

    texto_mutado = (
        "from proptech_core.acceso.dominio.identidad import Identidad  # noqa\n" + texto_original
    )
    assert texto_mutado != texto_original
    archivo_mutado.write_text(texto_mutado, encoding="utf-8")

    ofensores: list[str] = []
    for archivo in sorted(copia_de_compartido.rglob("*.py")):
        for level, module in _imports_de(archivo):
            if _primer_segmento_relevante(level, module) == "acceso":
                ofensores.append(archivo.name)
                break

    assert ofensores == ["base_de_datos.py"], ofensores


def test_compartido_no_importa_complejos() -> None:
    assert _archivos_que_importan("compartido", "complejos") == []


def test_compartido_no_importa_ningun_modulo_de_dominio() -> None:
    dominios = {
        "acceso",
        "complejos",
        "gastos",
        "liquidacion",
        "cuenta_corriente",
        "pagos",
        "avisos",
        "politicas",
    } | {
        p.name
        for p in RAIZ_SRC.iterdir()
        if p.is_dir() and p.name != "compartido" and not p.name.startswith("_")
    }
    ofensores = {
        d: archivos for d in dominios if (archivos := _archivos_que_importan("compartido", d))
    }
    assert ofensores == {}, ofensores
