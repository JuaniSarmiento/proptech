"""Fronteras entre módulos (D-021, design.md "Fronteras", cambio 2a, tarea
5.1): `compartido` no importa `acceso`, y `acceso` no importa `complejos`.
Recorre los imports con `ast`, nunca ejecutando el código de `proptech_core`.
"""

import ast
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

RAIZ_SRC = Path(
    os.environ.get("FRONTERAS_RAIZ", Path(__file__).resolve().parents[2] / "src" / "proptech_core")
)
RAIZ_API = Path(__file__).resolve().parents[2] / "src" / "proptech_api"


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
            for alias in nodo.names:
                if alias.name != "*":
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


# --- proptech_api no importa acceso.adaptadores (cliente de Clerk) ---
# (tarea 9.2): proptech_api es la capa HTTP y debe hablar con `acceso` sólo
# vía `aplicacion`/`dominio`; `adaptadores` es infraestructura (el cliente
# HTTP de Clerk) y no es parte del contrato de esa capa.


def _importa_adaptadores_de_acceso(archivo: Path) -> bool:
    """True si el archivo importa `proptech_core.acceso.adaptadores` o algo
    dentro, por cualquiera de las formas de import absoluto de Python."""
    objetivo = "proptech_core.acceso.adaptadores"
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name == objetivo or alias.name.startswith(objetivo + "."):
                    return True
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            if nodo.module == objetivo or nodo.module.startswith(objetivo + "."):
                return True
            if nodo.module == "proptech_core.acceso" and any(
                alias.name == "adaptadores" for alias in nodo.names
            ):
                return True
    return False


def test_proptech_api_no_importa_acceso_adaptadores() -> None:
    ofensores = [
        str(archivo.relative_to(RAIZ_API.parent))
        for archivo in sorted(RAIZ_API.rglob("*.py"))
        if _importa_adaptadores_de_acceso(archivo)
    ]
    assert ofensores == [], f"proptech_api no puede importar acceso.adaptadores: {ofensores}"


@pytest.fixture
def copia_de_proptech_api() -> Iterator[Path]:
    """Copia real de `proptech_api/` en una carpeta temporal (no el árbol
    del repo): la mutación no toca ni un byte del código real."""
    import shutil

    with tempfile.TemporaryDirectory() as carpeta:
        destino = Path(carpeta) / "proptech_api"
        shutil.copytree(RAIZ_API, destino)
        yield destino


def test_el_checker_encuentra_un_import_de_adaptadores_agregado_a_una_copia(
    copia_de_proptech_api: Path,
) -> None:
    archivo_mutado = copia_de_proptech_api / "acceso.py"
    texto_original = archivo_mutado.read_text(encoding="utf-8")
    assert "acceso.adaptadores" not in texto_original

    texto_mutado = (
        "from proptech_core.acceso.adaptadores.clerk_http import AdaptadorClerkHttp  # noqa\n"
        + texto_original
    )
    assert texto_mutado != texto_original
    archivo_mutado.write_text(texto_mutado, encoding="utf-8")

    ofensores = [
        archivo.name
        for archivo in sorted(copia_de_proptech_api.rglob("*.py"))
        if _importa_adaptadores_de_acceso(archivo)
    ]
    assert ofensores == ["acceso.py"], ofensores


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


@pytest.mark.parametrize(
    "sentencia",
    [
        "import proptech_core.compartido.cola",
        "from proptech_core.compartido import cola",
        "from proptech_core import compartido",
    ],
)
def test_recolector_conserva_submodulo(tmp_path: Path, sentencia: str) -> None:
    archivo = tmp_path / "ejemplo.py"
    archivo.write_text(sentencia)
    destino = (
        "proptech_core.compartido"
        if sentencia.endswith("import compartido")
        else "proptech_core.compartido.cola"
    )
    assert (0, destino) in _imports_de(archivo)


def _destinos(archivo: Path, raiz: Path) -> Iterator[tuple[bool, tuple[str, ...]]]:
    paquete = ("proptech_core", *archivo.relative_to(raiz).parts[:-1])
    for level, module in _imports_de(archivo):
        if module is None:
            continue
        partes = tuple(module.split("."))
        if level:
            partes = (*paquete[: len(paquete) - level + 1], *partes)
        yield bool(level), partes


def _modulos(raiz: Path) -> list[str]:
    return sorted(
        p.name
        for p in raiz.iterdir()
        if p.is_dir() and not p.name.startswith("_") and p.name != "compartido"
    )


def _ciclos(raiz: Path) -> list[str]:
    modulos = _modulos(raiz)
    grafo: dict[str, set[str]] = {m: set() for m in modulos}
    for origen in modulos:
        for archivo in (raiz / origen).rglob("*.py"):
            for _, destino in _destinos(archivo, raiz):
                if (
                    len(destino) > 1
                    and destino[0] == "proptech_core"
                    and destino[1] in grafo
                    and destino[1] != origen
                ):
                    grafo[origen].add(destino[1])
    ciclos: set[str] = set()

    def visitar(camino: list[str]) -> None:
        for siguiente in sorted(grafo[camino[-1]]):
            if siguiente in camino:
                ciclo = camino[camino.index(siguiente) :]
                inicio = ciclo.index(min(ciclo))
                ciclo = ciclo[inicio:] + ciclo[:inicio]
                ciclos.add(" → ".join([*ciclo, ciclo[0]]))
            else:
                visitar([*camino, siguiente])

    for modulo in modulos:
        visitar([modulo])
    return sorted(ciclos)


def test_sin_ciclos_entre_modulos() -> None:
    modulos = _modulos(RAIZ_SRC)
    assert "cuenta_corriente" in modulos, modulos
    print("Módulos recorridos:", modulos)
    assert _ciclos(RAIZ_SRC) == []


@pytest.fixture
def copia_core(tmp_path: Path) -> Path:
    import shutil

    destino = tmp_path / "proptech_core"
    shutil.copytree(RAIZ_SRC, destino)
    return destino


@pytest.mark.parametrize("tres", [False, True])
def test_ciclos_de_cualquier_largo(copia_core: Path, tres: bool) -> None:
    archivo = copia_core / "acceso" / "mutante.py"
    destino = "cuenta_corriente" if tres else "complejos"
    archivo.write_text(f"import proptech_core.{destino}.aplicacion")
    if tres:
        (copia_core / "cuenta_corriente" / "mutante.py").write_text(
            "import proptech_core.complejos.aplicacion"
        )
    esperado = (
        "acceso → cuenta_corriente → complejos → acceso" if tres else "acceso → complejos → acceso"
    )
    assert esperado in _ciclos(copia_core)


_EXCEPCIONES_ENTRE_MODULOS = {
    "acceso.dominio.eventos": "El vocabulario viaja con registrar y los eventos del padrón (D9)",
    "acceso.dominio.identidad": "Identidad viaja en los casos de uso auditados",
    "acceso.dominio.permisos": "Accion viaja en los casos de uso auditados",
}


def _entre_modulos(raiz: Path) -> list[str]:
    ofensores = []
    for origen in _modulos(raiz):
        for archivo in sorted((raiz / origen).rglob("*.py")):
            for relativo, destino in _destinos(archivo, raiz):
                if (
                    len(destino) < 2
                    or destino[0] != "proptech_core"
                    or destino[1] in (origen, "compartido")
                ):
                    continue
                publico = len(destino) > 2 and destino[2] == "aplicacion"
                excepcion = any(
                    destino[1 : 1 + len(d.split("."))] == tuple(d.split("."))
                    for d in _EXCEPCIONES_ENTRE_MODULOS
                )
                if relativo or not (publico or excepcion):
                    ofensores.append(f"{archivo.relative_to(raiz)}: {'.'.join(destino)}")
    return ofensores


def test_entre_modulos_solo_aplicacion() -> None:
    assert _entre_modulos(RAIZ_SRC) == []


@pytest.mark.parametrize(
    "sentencia,destino",
    [
        ("import proptech_core.acceso.dominio.token", "acceso.dominio.token"),
        ("from proptech_core.acceso.dominio import token", "acceso.dominio.token"),
        ("from proptech_core.acceso import dominio", "acceso.dominio"),
        ("import proptech_core.acceso.adaptadores", "acceso.adaptadores"),
        ("import proptech_core.acceso.dominio.identidad_x", "acceso.dominio.identidad_x"),
        ("from ...acceso.dominio import token", "acceso.dominio.token"),
    ],
)
def test_mutantes_entre_modulos(copia_core: Path, sentencia: str, destino: str) -> None:
    archivo = copia_core / "complejos" / "aplicacion" / "mutante.py"
    archivo.write_text(sentencia)
    ofensores = _entre_modulos(copia_core)
    assert any("mutante.py" in o and destino in o for o in ofensores), ofensores


_PUROS = {
    "dinero",
    "coeficientes",
    "porcentaje",
    "superficie",
    "texto",
    "tipos_de_unidad",
    "reparto",
}
_EXCEPCIONES_PUROS = {"parametros": "ConfiguracionEdificio.desde_parametros requiere Parametros"}


def _dominio_compartido(raiz: Path) -> list[str]:
    ofensores = []
    for archivo in sorted(raiz.rglob("*.py")):
        if "dominio" not in archivo.relative_to(raiz).parts:
            continue
        for _, destino in _destinos(archivo, raiz):
            if (
                destino[:2] == ("proptech_core", "compartido")
                and len(destino) > 2
                and destino[2] not in _PUROS | _EXCEPCIONES_PUROS.keys()
            ):
                ofensores.append(f"{archivo.relative_to(raiz)}: {'.'.join(destino)}")
    return ofensores


def _cuenta_corriente(raiz: Path) -> list[str]:
    ofensores = []
    for archivo in sorted((raiz / "cuenta_corriente").rglob("*.py")):
        for _, destino in _destinos(archivo, raiz):
            if destino[:3] == ("proptech_core", "compartido", "cola") or destino[:2] == (
                "proptech_core",
                "liquidacion",
            ):
                ofensores.append(f"{archivo.relative_to(raiz)}: {'.'.join(destino)}")
    return ofensores


def test_dominio_solo_usa_compartido_puro() -> None:
    assert _dominio_compartido(RAIZ_SRC) == []


def test_cuenta_corriente_no_encola_ni_liquida() -> None:
    assert _cuenta_corriente(RAIZ_SRC) == []


@pytest.mark.parametrize(
    "forma", ["import {d}", "from {p} import {n}", "from proptech_core import {mod}"]
)
@pytest.mark.parametrize("caso", ["base_de_datos", "nuevo", "cola"])
def test_mutantes_compartido(copia_core: Path, forma: str, caso: str) -> None:
    destino = f"proptech_core.compartido.{caso}"
    # La tercera forma importa compartido; se agrega el submódulo con from compartido.
    sentencia = forma.format(d=destino, p="proptech_core.compartido", n=caso, mod="compartido")
    if forma.endswith("{mod}"):
        sentencia = f"from proptech_core.compartido.{caso} import algo"
    if caso == "cola":
        archivo = copia_core / "cuenta_corriente" / "aplicacion" / "mutante.py"
        verificar = _cuenta_corriente
    else:
        archivo = copia_core / "complejos" / "dominio" / "mutante.py"
        verificar = _dominio_compartido
    (copia_core / "compartido" / "nuevo.py").touch()
    archivo.write_text(sentencia)
    ofensores = verificar(copia_core)
    assert any("mutante.py" in o and destino in o for o in ofensores), ofensores


def _dominio_sin_infraestructura(raiz: Path) -> list[str]:
    ofensores = []
    for archivo in sorted(raiz.rglob("*.py")):
        relativos = archivo.relative_to(raiz).parts
        if "dominio" not in relativos:
            continue
        for _, destino in _destinos(archivo, raiz):
            propio = (
                destino[:2] == ("proptech_core", relativos[0])
                and len(destino) > 2
                and destino[2] in {"aplicacion", "adaptadores", "puertos"}
            )
            if propio or destino[0] in {"sqlalchemy", "psycopg"}:
                ofensores.append(f"{archivo.relative_to(raiz)}: {'.'.join(destino)}")
    return ofensores


def test_dominio_no_depende_de_infraestructura() -> None:
    assert _dominio_sin_infraestructura(RAIZ_SRC) == []


@pytest.mark.parametrize("destino", ["sqlalchemy", "proptech_core.complejos.aplicacion.escritura"])
def test_mutantes_infraestructura(copia_core: Path, destino: str) -> None:
    archivo = copia_core / "complejos" / "dominio" / "mutante.py"
    archivo.write_text(f"import {destino}")
    assert any("mutante.py" in o and destino in o for o in _dominio_sin_infraestructura(copia_core))
