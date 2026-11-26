"""Aceptación de H-032: el prorrateo por días de la expensa del mes del cambio (change 4d `cambio-de-titular`,
CRITICAL; R32, D-168.5). Criterios en HISTORIAS.md, sección H-032. Sin chequeo de CI (D-154).

    python3 aceptacion/H-032/aceptar.py --sin-regresion    # por historia (la regresión, al cierre)
    python3 aceptacion/H-032/aceptar.py --local            # tests del árbol de trabajo (sin congelar)

  C01 a C06, N01 a N05  cada test lleva su criterio en el nombre.
  K01  la KB: la ficha 4 con H-032 y la deuda de anular un período con prorrateo, R32 con la parte del vendedor;
       los estructurales y, al cierre, H-004 a H-031 y el barrido. La lección de `15_lecciones.md` (o el "nada, porque") la revisa la persona en la demo.
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

RAMA = "change/cambio-de-titular"
CAMBIO = "cambio-de-titular"
#: El commit que congela esta aceptación (lo aprueba Juani). Vacío mientras se escribe.
ACEPTACION_SHA = "e451c6c"
CARPETA = "aceptacion/H-032/tests"
DESTINO = "backend/tests/integracion/aceptacion_h032"
TESTS_ESPERADOS = 23
CRITERIOS_DE_TESTS = [*(f"C{n:02d}" for n in range(1, 7)), *(f"N{n:02d}" for n in range(1, 6))]
BARRIDO = r"downgrade|\.migrar\(|alembic.*(up|down)grade|pg_restore"
#: Los tests estructurales del repo que esta historia toca (L-064, L-084, L-090).
ESTRUCTURALES = (
    "tests/unitarios/test_fronteras_de_modulos.py",
    "tests/unitarios/acceso/test_permisos.py",
    "tests/integracion/test_rutas_protegidas.py",
    "tests/integracion/test_vocabulario_configuracion.py",
    "tests/integracion/test_sesion_api.py",
)
H004 = ("H-004", "d2da37ef509cfb88ef62d5e12b5d4b3ec18d270e", 67)
#: H-030 y H-031 se congelaron con el SHA corto: acá van enteros.
H030 = ("H-030", "abbc1e2a2be6108cc1dd1844396ff61628c5e70a", 40)
H031 = ("H-031", "8601a7a7258045f175b8eca99017da9a3f327dcf", 27)
#: Tests de aceptaciones anteriores atados a su momento (L-082): sólo se perdonan con ese mensaje exacto.
CADUCOS = {
    "test_c17_la_0034_sube_y_baja_en_el_ciclo_de_devolucion": "la cabeza no es la 0034",
    "test_c20_la_0035_sube_y_baja_en_el_ciclo_de_devolucion": "la cabeza no es la 0035",
}
#: Tests que pasan antes de construir: el comportamiento ya existe (regresión).
NACEN_VERDES: dict[str, str] = {}

resultados: list[tuple[str, bool, str]] = []


def correr(*args: str, cwd: Path | None = None, chequear: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=chequear, stdin=subprocess.DEVNULL)


def anotar(criterio: str, ok: bool, detalle: str) -> None:
    resultados.append((criterio, ok, detalle))


def mostrar(arbol: str, ruta: str) -> str | None:
    r = correr("git", "show", f"{arbol}:{ruta}", chequear=False)
    return r.stdout if r.returncode == 0 else None


def copiar_desde(sha: str, carpeta: str, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in correr("git", "ls-tree", "--name-only", f"{sha}:{carpeta}").stdout.split():
        if nombre.endswith(".py"):
            (destino / nombre).write_text(mostrar(sha, f"{carpeta}/{nombre}") or "")


def copiar_tests(destino: Path, local: bool) -> None:
    if local:
        (destino / DESTINO).mkdir(parents=True)
        for f in Path(CARPETA).glob("*.py"):
            shutil.copy(f, destino / DESTINO / f.name)
        return
    if not ACEPTACION_SHA:
        sys.exit("ACEPTACION_SHA vacío: la aceptación no está congelada (usar --local para escribirla)")
    copiar_desde(ACEPTACION_SHA, CARPETA, destino / DESTINO)


def casos_de_junit(informe: Path) -> list[dict[str, str]]:
    casos = []
    for caso in ET.parse(informe).getroot().iter("testcase"):
        estado, mensaje = "pasa", ""
        for hijo, nombre in (("failure", "falla"), ("error", "error"), ("skipped", "skip")):
            elemento = caso.find(hijo)
            if elemento is not None:
                estado = nombre
                texto = elemento.get("message") or (elemento.text or "")
                mensaje = " ".join(texto.split())[:200]
                break
        casos.append({"nombre": caso.get("name", ""), "estado": estado, "mensaje": mensaje})
    return casos


def junit(backend: Path, *objetivos: str) -> tuple[int, list[dict[str, str]] | None, str]:
    with tempfile.TemporaryDirectory(prefix="aceptacion-h032-junit-") as tmp:
        informe = Path(tmp) / "junit.xml"
        corrida = correr("uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
                         f"--junitxml={informe}", *objetivos, cwd=backend, chequear=False)
        final = " | ".join((corrida.stdout + corrida.stderr).strip().splitlines()[-3:])
        if corrida.returncode not in (0, 1) or not informe.exists():
            return corrida.returncode, None, final
        return corrida.returncode, casos_de_junit(informe), final


def criterios_del_test(nombre: str) -> list[str]:
    m = re.match(r"test_((?:[cn]\d\d_)+)", nombre)
    return [t.upper() for t in m.group(1).split("_") if t] if m else []


def criterios_de_tests(casos: list[dict[str, str]]) -> None:
    por_criterio: dict[str, list[dict[str, str]]] = defaultdict(list)
    for caso in casos:
        for c in criterios_del_test(caso["nombre"].split("[")[0]):
            por_criterio[c].append(caso)
    for c in CRITERIOS_DE_TESTS:
        lista = por_criterio.get(c, [])
        malos = [x for x in lista if x["estado"] != "pasa"]
        if not lista:
            anotar(c, False, "ningún test corrió")
            continue
        detalle = f"{len(lista) - len(malos)} de {len(lista)} tests pasan"
        if malos:
            detalle += f"; el primero que no: {malos[0]['nombre']} ({malos[0]['estado']}: {malos[0]['mensaje']})"
        anotar(c, not malos, detalle)
    pasados = sum(x["estado"] == "pasa" for x in casos)
    conteo = {e: sum(x["estado"] == e for x in casos) for e in ("falla", "error", "skip")}
    anotar("TESTS", len(casos) == TESTS_ESPERADOS and pasados == TESTS_ESPERADOS,
           f"{TESTS_ESPERADOS} esperados; {len(casos)} ejecutados, {pasados} pasados, {conteo['falla']} fallas, "
           f"{conteo['error']} errores, {conteo['skip']} skips")
    inesperados = sorted({x["nombre"].split("[")[0] for x in casos if x["estado"] == "pasa"} - set(NACEN_VERDES))
    print(f"  (verdes fuera de NACEN_VERDES: {len(inesperados)})")


def caduco(caso: dict[str, str]) -> bool:
    return caso["estado"] != "pasa" and CADUCOS.get(caso["nombre"], "\0") in caso["mensaje"]


def congelada(historia: str) -> tuple[str, str, int]:
    """El SHA y la cantidad de tests de una aceptación anterior, leídos de su script en el repo."""
    texto = Path(f"aceptacion/{historia}/aceptar.py").read_text()
    sha = re.search(r'^ACEPTACION_SHA = "([0-9a-f]{40})"', texto, flags=re.M)
    esperados = re.search(r"^TESTS_ESPERADOS = (\d+)", texto, flags=re.M)
    if sha is None or esperados is None:
        sys.exit(f"no pude leer el SHA congelado de {historia} en aceptacion/{historia}/aceptar.py")
    return historia, sha.group(1), int(esperados.group(1))


def aceptacion_previa(destino: Path, historia: str, sha: str, esperados: int) -> list[str]:
    carpeta = f"backend/tests/integracion/aceptacion_{historia.lower().replace('-', '')}"
    copiar_desde(sha, f"aceptacion/{historia}/tests", destino / carpeta)
    codigo, casos, final = junit(destino / "backend", carpeta.removeprefix("backend/"))
    if casos is None:
        return [f"la aceptación de {historia} no corrió (código {codigo}): {final}"]
    pasados = sum(x["estado"] == "pasa" or caduco(x) for x in casos)
    if len(casos) != esperados or pasados != esperados:
        malos = [x for x in casos if x["estado"] != "pasa" and not caduco(x)]
        primero = f", el primero: {malos[0]['nombre']} ({malos[0]['mensaje']})" if malos else ""
        return [f"aceptación de {historia}: {pasados} de {len(casos)} (se esperan {esperados}){primero}"]
    return []


def barrido_de_migraciones(destino: Path) -> list[str]:
    backend = destino / "backend"
    lista = correr("rg", "-l", BARRIDO, "tests/integracion", "-g", "!**/aceptacion_h0*/**", cwd=backend,
                   chequear=False).stdout.split()
    if not lista:
        return ["el barrido de migraciones no encontró tests"]
    codigo, casos, final = junit(backend, *sorted(lista))
    if casos is None:
        return [f"el barrido de migraciones no corrió (código {codigo}): {final}"]
    malos = [x for x in casos if x["estado"] not in ("pasa", "skip")]
    if malos:
        return [f"barrido de migraciones: {len(malos)} de {len(casos)} no pasan, el primero: "
                f"{malos[0]['nombre']} ({malos[0]['mensaje']})"]
    return []


def estructurales(destino: Path) -> list[str]:
    codigo, casos, final = junit(destino / "backend", *ESTRUCTURALES)
    if casos is None:
        return [f"los tests estructurales no corrieron (código {codigo}): {final}"]
    malos = [x for x in casos if x["estado"] not in ("pasa", "skip")]
    return [f"tests estructurales: {len(malos)} no pasan, el primero: {malos[0]['nombre']} "
            f"({malos[0]['mensaje']})"] if malos else []


def seccion(texto: str, encabezado: str) -> str:
    m = re.search(rf"^(#+) {encabezado}[^\n]*\n.*?(?=^\1 |\Z)", texto, flags=re.S | re.M)
    return m.group(0) if m else ""


def leer(destino: Path, ruta: str) -> str:
    p = destino / ruta
    return p.read_text() if p.exists() else ""


def k01(destino: Path, sin_regresion: bool) -> None:
    faltas = []
    ficha = seccion(leer(destino, "knowledge-base/12_fichas_de_changes.md"), r"4 ·")
    if not re.search(r"4d · H-032 construida", ficha):
        faltas.append("la ficha 4 no registra `4d · H-032 construida`")
    if not re.search(r"(?is)anula\w*.{0,300}prorrateo|prorrateo.{0,300}anula\w*", ficha.split("4d · H-032 construida")[-1]):
        faltas.append("la ficha 4 no anota la deuda de anular un período con prorrateo aplicado (409)")
    if "parte_del_vendedor" not in seccion(leer(destino, "knowledge-base/05_reglas_de_negocio.md"), r"R32 "):
        faltas.append("R32 no nombra `parte_del_vendedor` en `05_reglas_de_negocio.md`")
    faltas += estructurales(destino)
    if sin_regresion:
        faltas.append("regresión no corrida (--sin-regresion)")
    else:
        previas = ("H-005", "H-006", "H-007", "H-008", "H-009", "H-010", "H-011", "H-012", "H-013", "H-014", "H-016",
                   "H-015", "H-017", "H-018", "H-019", "H-020", "H-021", "H-022", "H-023", "H-024", "H-025", "H-026",
                   "H-027", "H-028")
        for historia, sha, esperados in (H004, *(congelada(h) for h in previas), H030, H031):
            faltas += aceptacion_previa(destino, historia, sha, esperados)
        faltas += barrido_de_migraciones(destino)
    anotar("K01", not faltas, "; ".join(faltas) or "ficha 4, R32, estructurales, H-004 a H-031 y barrido")


def es_asercion(caso: dict[str, str]) -> bool:
    m = caso["mensaje"]
    return caso["estado"] == "falla" and m.startswith(("AssertionError", "assert", "Failed"))


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--codigo", help=f"commit o ref del código (por defecto, {RAMA})")
    argumentos.add_argument("--local", action="store_true", help="tests del árbol de trabajo (sin congelar)")
    argumentos.add_argument("--sin-regresion", action="store_true", help="saltea H-004 a H-031 y el barrido")
    a = argumentos.parse_args()
    codigo = correr("git", "rev-parse", a.codigo or RAMA).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="aceptacion-h032-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
        correr("git", "-C", str(destino), "checkout", "-q", "--detach", codigo)
        copiar_tests(destino, a.local)
        correr("uv", "sync", "-q", cwd=destino / "backend")
        rc, casos, final = junit(destino / "backend", "tests/integracion/aceptacion_h032")
        if casos is None:
            anotar("TESTS", False, f"pytest no corrió los tests (código {rc}): {final}")
            casos = []
        criterios_de_tests(casos)
        k01(destino, a.sin_regresion)
    origen = "árbol de trabajo (SIN CONGELAR)" if a.local else f"aceptación {ACEPTACION_SHA[:7]}"
    print(f"H-032 · código {codigo[:7]} · {origen}")
    orden = {c: n for n, c in enumerate(["TESTS", *CRITERIOS_DE_TESTS, "K01"])}
    for criterio, ok, detalle in sorted(resultados, key=lambda r: orden.get(r[0], 99)):
        print(f"  H-032.{criterio:<5} {'PASA ' if ok else 'FALLA'}  {detalle}")
    if casos:
        rojos = [x for x in casos if x["estado"] != "pasa"]
        no_asercion = [x for x in rojos if not es_asercion(x)]
        print(f"  rojos ({len(rojos)}); que no son por aserción ({len(no_asercion)}): "
              + ", ".join(f"{x['nombre']} [{x['estado']}: {x['mensaje'][:110]}]" for x in no_asercion))
    return 0 if resultados and all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
