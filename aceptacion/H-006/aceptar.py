"""Aceptación de H-006: situación de cobranza (4c `intereses-saldo-inicial-y-moroso`, parte 3, CRITICAL).
Criterios en HISTORIAS.md, sección H-006. Sin chequeo de CI (D-154: el CI corre al cerrar el change).

Se corre desde la raíz del repo, con `uv` y Docker andando (los tests levantan su propio PostgreSQL con
testcontainers):

    python3 aceptacion/H-006/aceptar.py                    # código: la rama del 4c
    python3 aceptacion/H-006/aceptar.py --codigo <ref>     # otro commit
    python3 aceptacion/H-006/aceptar.py --local            # tests del árbol de trabajo, no del SHA
                                                           # congelado: sólo para escribirla
    python3 aceptacion/H-006/aceptar.py --sin-regresion    # saltea las aceptaciones de H-004 y H-005
                                                           # (C19 queda en FALLA)

Qué hace, sin tocar el árbol de trabajo: clona el repo con `--shared`, deja el clon en el commit del
código, copia los tests de la aceptación **desde el SHA congelado** (`ACEPTACION_SHA`) a
`backend/tests/integracion/aceptacion_h006/` del clon y corre pytest con `--junitxml`.

  C01 a C16  cada test lleva su criterio en el nombre (`test_c04_…`); un criterio pasa si todos sus
             tests corren y pasan, y la corrida entera tiene los `TESTS_ESPERADOS`, sin skips ni errores.
  C17  la base de conocimiento: R20 con "$500 o más" o `>=` (no "supera") y dónde vive (`cobranza`), R30
       con dónde vive, el glosario (situación de cobranza, fecha de clasificación, deuda de intereses) y
       la ficha del 4c con H-006.
  C18  cada escenario de la spec `situacion-de-cobranza` está en el docstring (`Escenario: <título>`) de
       un test que corrió y pasó.
  C19  las aceptaciones de H-004 (desde su SHA congelado, 67/67) y de H-005 (desde el SHA que fija
       `aceptacion/H-005/aceptar.py`, todos sus tests) siguen en verde sobre el mismo código.

Sale con 0 sólo si todos los criterios pasan.
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

RAMA = "change/intereses-por-mora"
CAMBIO = "intereses-saldo-inicial-y-moroso"
#: El commit que congela esta aceptación (por delegación de Juani). Vacío mientras se escribe.
ACEPTACION_SHA = "3f6629bbdbc69ca81f31b1716a28a9d1c1fc1401"
CARPETA = "aceptacion/H-006/tests"
DESTINO = "backend/tests/integracion/aceptacion_h006"
#: Las aceptaciones anteriores del change, congeladas, que tienen que seguir en verde (C19).
H004_SHA = "d2da37ef509cfb88ef62d5e12b5d4b3ec18d270e"
H004_ESPERADOS = 67
TESTS_ESPERADOS = 33
CRITERIOS_DE_TESTS = [f"C{n:02d}" for n in range(1, 17)]
SPEC = "situacion-de-cobranza"
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
    destino.mkdir(parents=True)
    for nombre in correr("git", "ls-tree", "--name-only", f"{sha}:{carpeta}").stdout.split():
        if nombre.endswith(".py"):
            (destino / nombre).write_text(mostrar(sha, f"{carpeta}/{nombre}") or "")


def copiar_tests(destino: Path, local: bool) -> None:
    carpeta = destino / DESTINO
    if local:
        carpeta.mkdir(parents=True)
        for f in Path(CARPETA).glob("*.py"):
            shutil.copy(f, carpeta / f.name)
        return
    if not ACEPTACION_SHA:
        sys.exit("ACEPTACION_SHA vacío: la aceptación no está congelada (usar --local para escribirla)")
    copiar_desde(ACEPTACION_SHA, CARPETA, carpeta)


def junit(backend: Path, *objetivos: str) -> tuple[int, list[dict[str, str]] | None, str]:
    with tempfile.TemporaryDirectory(prefix="aceptacion-h006-junit-") as tmp:
        informe = Path(tmp) / "junit.xml"
        corrida = correr("uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
                         f"--junitxml={informe}", *objetivos, cwd=backend, chequear=False)
        final = " | ".join((corrida.stdout + corrida.stderr).strip().splitlines()[-3:])
        if corrida.returncode not in (0, 1) or not informe.exists():
            return corrida.returncode, None, final
        casos = []
        for caso in ET.parse(informe).getroot().iter("testcase"):
            estado, mensaje = "pasa", ""
            for hijo, nombre in (("failure", "falla"), ("error", "error"), ("skipped", "skip")):
                elemento = caso.find(hijo)
                if elemento is not None:
                    estado = nombre
                    mensaje = (elemento.get("message") or "").splitlines()[0][:160] if elemento.get("message") else ""
                    break
            casos.append({"nombre": caso.get("name", ""), "estado": estado, "mensaje": mensaje})
        return corrida.returncode, casos, final


def criterios_del_test(nombre: str) -> list[str]:
    m = re.match(r"test_((?:c\d\d_)+)", nombre)
    return [f"C{t[1:]}" for t in m.group(1).split("_") if t] if m else []


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




def h005_congelada() -> tuple[str, int]:
    """El SHA y la cantidad de tests de la aceptación de H-005, leídos de su script en el repo."""
    texto = Path("aceptacion/H-005/aceptar.py").read_text()
    sha = re.search(r'^ACEPTACION_SHA = "([0-9a-f]{40})"', texto, flags=re.M)
    esperados = re.search(r"^TESTS_ESPERADOS = (\d+)", texto, flags=re.M)
    if sha is None or esperados is None:
        sys.exit("no pude leer el SHA congelado de H-005 en aceptacion/H-005/aceptar.py")
    return sha.group(1), int(esperados.group(1))


def aceptacion_previa(destino: Path, historia: str, sha: str, esperados: int) -> list[str]:
    carpeta = f"backend/tests/integracion/aceptacion_{historia.lower().replace('-', '')}"
    copiar_desde(sha, f"aceptacion/{historia}/tests", destino / carpeta)
    codigo, casos, final = junit(destino / "backend", carpeta.removeprefix("backend/"))
    if casos is None:
        return [f"la aceptación de {historia} no corrió (código {codigo}): {final}"]
    pasados = sum(x["estado"] == "pasa" for x in casos)
    if len(casos) != esperados or pasados != esperados:
        malos = [x for x in casos if x["estado"] != "pasa"]
        primero = f", el primero: {malos[0]['nombre']} ({malos[0]['mensaje']})" if malos else ""
        return [f"aceptación de {historia}: {pasados} de {len(casos)} (se esperan {esperados}){primero}"]
    return []


def c17(destino: Path) -> None:
    def leer(ruta: str) -> str:
        p = destino / ruta
        return p.read_text() if p.exists() else ""

    def regla(texto: str, numero: str) -> str:
        m = re.search(rf"^## {numero}\b[^\n]*\n.*?(?=^## R\d\d\b|\Z)", texto, flags=re.S | re.M)
        return m.group(0) if m else ""

    faltas = []
    reglas = leer("knowledge-base/05_reglas_de_negocio.md")
    r20, r30 = regla(reglas, "R20"), regla(reglas, "R30")
    if not r20:
        faltas.append("no está R20")
    else:
        if re.search(r"\bsupera\b", r20):
            faltas.append("R20 todavía dice «supera» (E6: $500 o más)")
        if not re.search(r"\$500 o más|>=|≥", r20):
            faltas.append("R20 no dice «$500 o más» ni `>=`")
        if "cobranza" not in r20:
            faltas.append("R20 no dice dónde vive (`cobranza`)")
    if "cobranza" not in r30:
        faltas.append("R30 no dice dónde vive (`cobranza`)")
    glosario = leer("knowledge-base/11_glosario.md")
    for termino in ("situación de cobranza", "fecha de clasificación", "deuda de intereses"):
        if not re.search(rf"\*\*{termino}\*\*", glosario, flags=re.I):
            faltas.append(f"el glosario no define «{termino}»")
    fichas = leer("knowledge-base/12_fichas_de_changes.md")
    ficha = re.search(r"^#{3,5} 4c\b[^\n]*\n.*?(?=^#{3,4} |\Z)", fichas, flags=re.S | re.M)
    if ficha is None or "H-006" not in ficha.group(0):
        faltas.append("la ficha del 4c no registra H-006")
    anotar("C17", not faltas, "; ".join(faltas) or "R20, R30, el glosario y la ficha del 4c al día")


def c18(destino: Path, casos: list[dict[str, str]] | None) -> None:
    candidatos = [destino / f"openspec/changes/{CAMBIO}/specs/{SPEC}/spec.md",
                  *sorted((destino / "openspec/changes/archive").glob(f"*-{CAMBIO}/specs/{SPEC}/spec.md")),
                  destino / f"openspec/specs/{SPEC}/spec.md"]
    texto = next((p.read_text() for p in candidatos if p.exists()), None)
    if texto is None:
        anotar("C18", False, f"no está la spec {SPEC}")
        return
    titulos = re.findall(r"^#### Scenario: (.+?)\s*$", texto, flags=re.M)
    verdes = {x["nombre"].split("[")[0] for x in casos or [] if x["estado"] == "pasa"}
    malos = {x["nombre"].split("[")[0] for x in casos or [] if x["estado"] != "pasa"}
    cubiertos: dict[str, set[str]] = defaultdict(set)
    for archivo in (destino / DESTINO).glob("test_*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text())):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                for titulo in re.findall(r"Escenario: (.+)", ast.get_docstring(nodo) or ""):
                    cubiertos[titulo.strip()].add(nodo.name)
    sin_test = [t for t in titulos if not cubiertos.get(t)]
    sin_verde = [t for t in titulos if cubiertos.get(t) and (not cubiertos[t] & verdes or cubiertos[t] & malos)]
    faltas = []
    if sin_test:
        faltas.append(f"{len(sin_test)} escenarios sin test, el primero «{sin_test[0]}»")
    if sin_verde:
        faltas.append(f"{len(sin_verde)} escenarios con tests que no pasan, el primero «{sin_verde[0]}»")
    anotar("C18", not faltas, "; ".join(faltas) or f"{len(titulos)} escenarios de {SPEC}, cada uno con su test en verde")


def c19(destino: Path, sin_regresion: bool) -> None:
    if sin_regresion:
        anotar("C19", False, "regresión no corrida (--sin-regresion)")
        return
    h005_sha, h005_esperados = h005_congelada()
    faltas = aceptacion_previa(destino, "H-004", H004_SHA, H004_ESPERADOS)
    faltas += aceptacion_previa(destino, "H-005", h005_sha, h005_esperados)
    anotar("C19", not faltas, "; ".join(faltas) or
           f"H-004 {H004_ESPERADOS}/{H004_ESPERADOS} y H-005 {h005_esperados}/{h005_esperados} en verde")


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--codigo", help=f"commit o ref del código (por defecto, {RAMA})")
    argumentos.add_argument("--local", action="store_true", help="tests del árbol de trabajo (sin congelar)")
    argumentos.add_argument("--sin-regresion", action="store_true", help="saltea H-004 y H-005 (C19 falla)")
    a = argumentos.parse_args()
    codigo = correr("git", "rev-parse", a.codigo or RAMA).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="aceptacion-h006-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
        correr("git", "-C", str(destino), "checkout", "-q", "--detach", codigo)
        copiar_tests(destino, a.local)
        correr("uv", "sync", "-q", cwd=destino / "backend")
        rc, casos, final = junit(destino / "backend", "tests/integracion/aceptacion_h006")
        if casos is None:
            anotar("TESTS", False, f"pytest no corrió los tests (código {rc}): {final}")
        else:
            criterios_de_tests(casos)
        c17(destino)
        c18(destino, casos)
        c19(destino, a.sin_regresion)
    origen = "árbol de trabajo (SIN CONGELAR)" if a.local else f"aceptación {ACEPTACION_SHA[:7]}"
    print(f"H-006 · código {codigo[:7]} · {origen}")
    orden = {c: n for n, c in enumerate(["TESTS", *CRITERIOS_DE_TESTS, "C17", "C18", "C19"])}
    for criterio, ok, detalle in sorted(resultados, key=lambda r: orden.get(r[0], 99)):
        print(f"  H-006.{criterio:<5} {'PASA ' if ok else 'FALLA'}  {detalle}")
    if casos:
        verdes = sorted(x["nombre"] for x in casos if x["estado"] == "pasa")
        print(f"  verdes ({len(verdes)}): {', '.join(verdes)}")
        rojos = [x for x in casos if x["estado"] != "pasa"]
        no_asercion = [x for x in rojos if x["estado"] == "error" or not x["mensaje"].startswith(("AssertionError", "assert", "Failed"))]
        print(f"  rojos ({len(rojos)}); que no son por aserción ({len(no_asercion)}): "
              + ", ".join(f"{x['nombre']} [{x['estado']}: {x['mensaje'][:90]}]" for x in no_asercion))
    return 0 if resultados and all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
