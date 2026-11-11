"""Aceptación de H-004: interés por mora al emitir (4c `intereses-saldo-inicial-y-moroso`, parte 1,
CRITICAL). Criterios en HISTORIAS.md, sección H-004.

Se corre desde la raíz del repo, con `gh` autenticado, `uv` y Docker andando (los tests levantan su
propio PostgreSQL con testcontainers):

    python3 aceptacion/H-004/aceptar.py                 # código: la cabeza del PR del 4c
    python3 aceptacion/H-004/aceptar.py --codigo <ref>  # otro commit (por ejemplo origin/main)
    python3 aceptacion/H-004/aceptar.py --local         # tests del árbol de trabajo, no del SHA
                                                        # congelado: sólo para escribirla

Qué hace, sin tocar el árbol de trabajo: clona el repo con `--shared` (no un worktree: los scripts
de infra escriben en `.git/`), deja el clon en el commit del código, copia los tests de la aceptación
**desde el SHA congelado** (`ACEPTACION_SHA`) a `backend/tests/integracion/aceptacion_h004/` del clon
(así usan el `conftest.py` y las fixtures del repo) y corre pytest con `--junitxml`.

  C01 a C16, C19 a C27  cada test lleva su criterio en el nombre (`test_c07_c13_…`); un criterio
                        pasa si todos sus tests corren y pasan, y la corrida entera tiene los
                        `TESTS_ESPERADOS`, sin skips ni errores.
  C17  el test del ciclo de la 0034 pasa; el CI del PR está en verde (al menos `CHECKS_MINIMOS`
       checks y un run de `pull_request`); ningún test queda atado a la `0033` como cabeza; los
       tests `test_cc_*` y `test_libro*` de `origin/main` siguen todos en el código.
  C18  la base de conocimiento nombra el corte y los tramos en R03, R17 con la re-emisión, y
       `tramo_de_interes` en 04, 08, 11 y la ficha del 4c.
  C28  cada escenario de las specs `intereses-por-mora`, `libro-de-movimientos` y
       `reparto-de-montos` está en el docstring (`Escenario: <título>`) de un test que corrió y
       pasó.

Sale con 0 sólo si todos los criterios pasan.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

REPO = "JuaniSarmiento/proptech"
RAMA_DEL_PR = "change/intereses-por-mora"
CAMBIO = "intereses-saldo-inicial-y-moroso"
#: El commit que congela esta aceptación (lo aprueba Juani). Vacío mientras se escribe.
ACEPTACION_SHA = ""
CARPETA = "aceptacion/H-004/tests"
DESTINO = "backend/tests/integracion/aceptacion_h004"
TESTS_ESPERADOS = 67
CHECKS_MINIMOS = 6
CRITERIOS_DE_TESTS = [f"C{n:02d}" for n in (*range(1, 17), *range(19, 28))]
SPECS = ("intereses-por-mora", "libro-de-movimientos", "reparto-de-montos")
#: Tests que pasan sobre `main` antes de construir: el comportamiento ya existe (regresión).
NACEN_VERDES = {
    "test_c12_edificio_de_otra_administracion": "la FK de `emision` ya rechaza el edificio ajeno (4b)",
    "test_c15_el_medio_sube": "redondeo medio hacia arriba del 4a",
    "test_c15_float_rechazado": "el float ya se rechaza (4a)",
    "test_c09_una_sola_lectura_al_publicar_una_emision_nueva": "RF-01: una sola foto ya en el 4b",
    "test_c09_una_sola_lectura_al_repetir_una_emision": "RF-04: el replay ya lee una sola foto",
    "test_c16_anulacion_durante_un_credito_de_correccion": "RF-02: la anulación ya bloquea (4b)",
    "test_c16_anulacion_durante_un_contra_asiento": "RF-02: el contra-asiento ya pasa por el candado",
}

resultados: list[tuple[str, bool, str]] = []


def correr(*args: str, cwd: Path | None = None, chequear: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=chequear, stdin=subprocess.DEVNULL)


def anotar(criterio: str, ok: bool, detalle: str) -> None:
    resultados.append((criterio, ok, detalle))


def mostrar(arbol: str, ruta: str, cwd: Path | None = None) -> str | None:
    r = correr("git", "show", f"{arbol}:{ruta}", cwd=cwd, chequear=False)
    return r.stdout if r.returncode == 0 else None


def cabeza_del_pr() -> tuple[str, int | None]:
    prs = json.loads(correr("gh", "pr", "list", "--repo", REPO, "--head", RAMA_DEL_PR, "--state", "all",
                            "--json", "number,headRefOid").stdout)
    if not prs:
        return "", None
    return prs[0]["headRefOid"], prs[0]["number"]


def copiar_tests(destino: Path, local: bool) -> None:
    carpeta = destino / DESTINO
    carpeta.mkdir(parents=True)
    if local:
        for f in Path(CARPETA).glob("*.py"):
            shutil.copy(f, carpeta / f.name)
        return
    if not ACEPTACION_SHA:
        sys.exit("ACEPTACION_SHA vacío: la aceptación no está congelada (usar --local para escribirla)")
    nombres = correr("git", "ls-tree", "--name-only", f"{ACEPTACION_SHA}:{CARPETA}").stdout.split()
    for nombre in nombres:
        if nombre.endswith(".py"):
            (carpeta / nombre).write_text(mostrar(ACEPTACION_SHA, f"{CARPETA}/{nombre}") or "")


def criterios_del_test(nombre: str) -> list[str]:
    m = re.match(r"test_((?:c\d\d_)+)", nombre)
    return [f"C{t[1:]}" for t in m.group(1).split("_") if t] if m else []


def correr_tests(destino: Path) -> list[dict[str, str]] | None:
    backend = destino / "backend"
    correr("uv", "sync", "-q", cwd=backend)
    with tempfile.TemporaryDirectory(prefix="aceptacion-h004-junit-") as tmp:
        informe = Path(tmp) / "junit.xml"
        corrida = correr("uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
                         f"--junitxml={informe}", "tests/integracion/aceptacion_h004", cwd=backend, chequear=False)
        if corrida.returncode not in (0, 1) or not informe.exists():
            final = (corrida.stdout + corrida.stderr).strip().splitlines()[-5:]
            anotar("TESTS", False, f"pytest no corrió los tests (código {corrida.returncode}): {' | '.join(final)}")
            return None
        casos = []
        for caso in ET.parse(informe).getroot().iter("testcase"):
            estado = "pasa"
            for hijo, nombre in (("failure", "falla"), ("error", "error"), ("skipped", "skip")):
                elemento = caso.find(hijo)
                if elemento is not None:
                    estado = nombre
                    casos.append({"nombre": caso.get("name", ""), "estado": estado,
                                  "mensaje": (elemento.get("message") or "").splitlines()[0][:160] if elemento.get("message") else ""})
                    break
            else:
                casos.append({"nombre": caso.get("name", ""), "estado": estado, "mensaje": ""})
        return casos


def criterios_de_tests(casos: list[dict[str, str]]) -> None:
    por_criterio: dict[str, list[dict[str, str]]] = defaultdict(list)
    for caso in casos:
        base = caso["nombre"].split("[")[0]
        for c in criterios_del_test(base):
            por_criterio[c].append(caso)
    for c in [*CRITERIOS_DE_TESTS, "C17"]:
        lista = por_criterio.get(c, [])
        malos = [x for x in lista if x["estado"] != "pasa"]
        if c == "C17":
            continue
        if not lista:
            anotar(c, False, "ningún test corrió")
        else:
            detalle = f"{len(lista) - len(malos)} de {len(lista)} tests pasan"
            if malos:
                detalle += f"; el primero que no: {malos[0]['nombre']} ({malos[0]['estado']}: {malos[0]['mensaje']})"
            anotar(c, not malos, detalle)
    total = len(casos)
    pasados = sum(x["estado"] == "pasa" for x in casos)
    conteo = {e: sum(x["estado"] == e for x in casos) for e in ("falla", "error", "skip")}
    verdes_inesperados = sorted({x["nombre"].split("[")[0] for x in casos if x["estado"] == "pasa"} - set(NACEN_VERDES))
    anotar("TESTS", total == TESTS_ESPERADOS and pasados == TESTS_ESPERADOS,
           f"{TESTS_ESPERADOS} esperados; {total} ejecutados, {pasados} pasados, {conteo['falla']} fallas, "
           f"{conteo['error']} errores, {conteo['skip']} skips")
    print(f"  (verdes fuera de NACEN_VERDES: {len(verdes_inesperados)})")
    return None


def c17(destino: Path, casos: list[dict[str, str]] | None, cabeza: str, pr: int | None) -> None:
    faltas = []
    ciclo = [x for x in casos or [] if x["nombre"].startswith("test_c17_")]
    if not ciclo or any(x["estado"] != "pasa" for x in ciclo):
        faltas.append("el ciclo de la 0034 no pasa" + (f" ({ciclo[0]['mensaje']})" if ciclo else ""))
    if pr is None:
        faltas.append(f"no hay PR de {RAMA_DEL_PR}")
    else:
        corridas = json.loads(correr("gh", "api", f"repos/{REPO}/commits/{cabeza}/check-runs").stdout)["check_runs"]
        malas = [c["name"] for c in corridas if c["status"] != "completed" or c["conclusion"] not in ("success", "skipped")]
        runs = json.loads(correr("gh", "run", "list", "--repo", REPO, "--commit", cabeza, "--event", "pull_request",
                                 "--json", "conclusion").stdout)
        if len(corridas) < CHECKS_MINIMOS or malas or not any(r["conclusion"] == "success" for r in runs):
            faltas.append(f"CI del PR #{pr}: {len(corridas)} checks, no verdes {malas}, runs pull_request {len(runs)}")
    atados = correr("rg", "-n", '"0033"', "backend/tests", "-g", "!**/aceptacion_h004/**", cwd=destino, chequear=False).stdout
    atados_a_la_cabeza = [l for l in atados.splitlines() if not re.search(r"downgrade|bajar|baja|0034", l)]
    if atados_a_la_cabeza:
        faltas.append(f"{len(atados_a_la_cabeza)} líneas con \"0033\" fuera de una bajada, la primera: {atados_a_la_cabeza[0][:120]}")
    faltas += regresion_de_los_tests_del_4b(destino)
    anotar("C17", not faltas, "; ".join(faltas) or "ciclo de la 0034, CI verde, sin 0033 como cabeza, tests del 4b enteros")


def coleccion(backend: Path) -> set[str]:
    r = correr("uv", "run", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-k", "test_cc_ or test_libro",
               "tests/integracion", cwd=backend, chequear=False)
    return {l.strip() for l in r.stdout.splitlines() if "::" in l and not l.startswith("tests/integracion/aceptacion_h004")}


def regresion_de_los_tests_del_4b(destino: Path) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="aceptacion-h004-main-") as tmp:
        main = Path(tmp) / "main"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(main))
        sha = correr("git", "rev-parse", "origin/main").stdout.strip()
        correr("git", "-C", str(main), "checkout", "-q", "--detach", sha)
        correr("uv", "sync", "-q", cwd=main / "backend")
        antes = coleccion(main / "backend")
    despues = coleccion(destino / "backend")
    faltan = sorted(antes - despues)
    if not antes:
        return ["no se pudieron coleccionar los tests del 4b en origin/main"]
    return [f"faltan {len(faltan)} tests del 4b, el primero: {faltan[0]}"] if faltan else []


def c18(destino: Path) -> None:
    def leer(ruta: str) -> str:
        p = destino / ruta
        return p.read_text() if p.exists() else ""

    faltas = []
    reglas = leer("knowledge-base/05_reglas_de_negocio.md")
    r03 = re.search(r"^## R03\b[^\n]*\n.*?(?=^## R\d\d\b|\Z)", reglas, flags=re.S | re.M)
    if r03 is None or not re.search(r"\bcorte\b", r03.group(0)) or not re.search(r"\btramo", r03.group(0)):
        faltas.append("R03 no nombra el corte y los tramos")
    r17 = re.search(r"^## R17\b[^\n]*\n.*?(?=^## R\d\d\b|\Z)", reglas, flags=re.S | re.M)
    if r17 is None or not re.search(r"corte siguiente|re-?emisi", r17.group(0)):
        faltas.append("R17 no dice qué pasa con el interés al re-emitir")
    for ruta in ("knowledge-base/04_modelo_de_datos.md", "knowledge-base/08_arquitectura_propuesta.md"):
        if "tramo_de_interes" not in leer(ruta):
            faltas.append(f"{ruta.split('/')[-1]} no nombra tramo_de_interes")
    if not re.search(r"tramo de inter[eé]s", leer("knowledge-base/11_glosario.md"), flags=re.I):
        faltas.append("el glosario no define el tramo de interés")
    fichas = leer("knowledge-base/12_fichas_de_changes.md")
    ficha = re.search(r"^#{3,5} 4c\b[^\n]*\n.*?(?=^#{3,4} |\Z)", fichas, flags=re.S | re.M)
    if ficha is None or "H-004" not in ficha.group(0):
        faltas.append("la ficha del 4c no registra H-004")
    anotar("C18", not faltas, "; ".join(faltas) or "R03, R17, 04, 08, 11 y la ficha del 4c al día")


def escenarios(destino: Path) -> dict[str, list[str]]:
    encontrados: dict[str, list[str]] = {}
    for spec in SPECS:
        candidatos = [destino / f"openspec/changes/{CAMBIO}/specs/{spec}/spec.md",
                      *sorted((destino / "openspec/changes/archive").glob(f"*-{CAMBIO}/specs/{spec}/spec.md"))]
        texto = next((p.read_text() for p in candidatos if p.exists()), None)
        if texto is not None:
            encontrados[spec] = re.findall(r"^#### Scenario: (.+?)\s*$", texto, flags=re.M)
    return encontrados


def c28(destino: Path, casos: list[dict[str, str]] | None) -> None:
    verdes = {x["nombre"].split("[")[0] for x in casos or [] if x["estado"] == "pasa"}
    malos = {x["nombre"].split("[")[0] for x in casos or [] if x["estado"] != "pasa"}
    cubiertos: dict[str, set[str]] = defaultdict(set)
    for archivo in (destino / DESTINO).glob("test_*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text())):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                for titulo in re.findall(r"Escenario: (.+)", ast.get_docstring(nodo) or ""):
                    cubiertos[titulo.strip()].add(nodo.name)
    por_spec = escenarios(destino)
    faltas = [f"no está la spec {s}" for s in SPECS if s not in por_spec]
    sin_test, sin_verde = [], []
    for spec, titulos in por_spec.items():
        for t in titulos:
            tests = cubiertos.get(t, set())
            if not tests:
                sin_test.append(f"{spec}: {t}")
            elif not tests & verdes or tests & malos:
                sin_verde.append(f"{spec}: {t}")
    total = sum(len(t) for t in por_spec.values())
    if sin_test:
        faltas.append(f"{len(sin_test)} escenarios sin test, el primero «{sin_test[0]}»")
    if sin_verde:
        faltas.append(f"{len(sin_verde)} escenarios con tests que no pasan, el primero «{sin_verde[0]}»")
    anotar("C28", not faltas, "; ".join(faltas) or f"{total} escenarios de {len(por_spec)} specs, cada uno con su test en verde")


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--codigo", help="commit o ref del código a verificar (por defecto, la cabeza del PR)")
    argumentos.add_argument("--local", action="store_true", help="tests del árbol de trabajo (sin congelar)")
    a = argumentos.parse_args()
    correr("git", "fetch", "-q", "origin")
    cabeza, pr = cabeza_del_pr()
    codigo = correr("git", "rev-parse", a.codigo or cabeza or "origin/main").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="aceptacion-h004-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
        correr("git", "-C", str(destino), "checkout", "-q", "--detach", codigo)
        copiar_tests(destino, a.local)
        casos = correr_tests(destino)
        if casos is not None:
            criterios_de_tests(casos)
        c17(destino, casos, codigo, pr if codigo == cabeza else None)
        c18(destino)
        c28(destino, casos)
    origen = "árbol de trabajo (SIN CONGELAR)" if a.local else f"aceptación {ACEPTACION_SHA[:7]}"
    print(f"H-004 · código {codigo[:7]}" + (f" (PR #{pr})" if pr and codigo == cabeza else "") + f" · {origen}")
    orden = {c: n for n, c in enumerate(["TESTS", *CRITERIOS_DE_TESTS, "C17", "C18", "C28"])}
    for criterio, ok, detalle in sorted(resultados, key=lambda r: orden.get(r[0], 99)):
        print(f"  H-004.{criterio:<5} {'PASA ' if ok else 'FALLA'}  {detalle}")
    if casos:
        verdes = sorted(x["nombre"] for x in casos if x["estado"] == "pasa")
        print(f"  verdes ({len(verdes)}): {', '.join(verdes)}")
    return 0 if resultados and all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
