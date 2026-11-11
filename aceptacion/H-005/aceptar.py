"""Aceptación de H-005: saldo inicial (4c `intereses-saldo-inicial-y-moroso`, parte 2, CRITICAL).
Criterios en HISTORIAS.md, sección H-005. Sin chequeo de CI (D-154: el CI corre al cerrar el change).

Se corre desde la raíz del repo, con `uv` y Docker andando (los tests levantan su propio PostgreSQL con
testcontainers):

    python3 aceptacion/H-005/aceptar.py                    # código: la rama del 4c
    python3 aceptacion/H-005/aceptar.py --codigo <ref>     # otro commit
    python3 aceptacion/H-005/aceptar.py --local            # tests del árbol de trabajo, no del SHA
                                                           # congelado: sólo para escribirla
    python3 aceptacion/H-005/aceptar.py --sin-regresion    # saltea la aceptación de H-004 y el barrido
                                                           # de migraciones (C20 queda en FALLA)

Qué hace, sin tocar el árbol de trabajo: clona el repo con `--shared` (no un worktree: los scripts de
infra escriben en `.git/`), deja el clon en el commit del código, copia los tests de la aceptación
**desde el SHA congelado** (`ACEPTACION_SHA`) a `backend/tests/integracion/aceptacion_h005/` del clon y
corre pytest con `--junitxml`.

  C01 a C19  cada test lleva su criterio en el nombre (`test_c13_…`); un criterio pasa si todos sus
             tests corren y pasan, y la corrida entera tiene los `TESTS_ESPERADOS`, sin skips ni errores.
  C20  el test del ciclo de la 0035 pasa; `infra/ci/ensayo-roles.sh` devuelve las dos tablas nuevas al
       migrador; la aceptación de H-004 (desde su SHA congelado) sigue 67/67; los tests `test_cc_*` y
       `test_libro*` de `origin/main` siguen todos; los tests que bajan o restauran migraciones pasan.
  C21  la base de conocimiento: R09 con la carga de saldo inicial y la firma del pedido, las dos
       tablas en 04 y 08, el glosario y la ficha del 4c con H-005.
  C22  cada escenario de la spec `saldo-inicial` está en el docstring (`Escenario: <título>`) de un test
       que corrió y pasó.

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
#: El commit que congela esta aceptación (lo aprueba Juani). Vacío mientras se escribe.
ACEPTACION_SHA = "0b4c5cb69628cd69c7a6ee49ac27f3fb439c1234"
CARPETA = "aceptacion/H-005/tests"
DESTINO = "backend/tests/integracion/aceptacion_h005"
#: La aceptación de H-004, congelada, que tiene que seguir en verde (C20).
H004_SHA = "d2da37ef509cfb88ef62d5e12b5d4b3ec18d270e"
H004_CARPETA = "aceptacion/H-004/tests"
H004_DESTINO = "backend/tests/integracion/aceptacion_h004"
H004_ESPERADOS = 67
TESTS_ESPERADOS = 60
CRITERIOS_DE_TESTS = [f"C{n:02d}" for n in range(1, 20)]
SPEC = "saldo-inicial"
TABLAS = ("carga_de_saldo_inicial", "origen_de_saldo_inicial")
#: Los tests que bajan o restauran migraciones (L-064: lo que el CI encontró tarde en H-004).
BARRIDO = r"downgrade|\.migrar\(|alembic.*(up|down)grade|pg_restore"
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
    with tempfile.TemporaryDirectory(prefix="aceptacion-h005-junit-") as tmp:
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


def coleccion(backend: Path) -> set[str]:
    r = correr("uv", "run", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-k", "test_cc_ or test_libro",
               "tests/integracion", cwd=backend, chequear=False)
    return {l.strip() for l in r.stdout.splitlines() if "::" in l and "/aceptacion_h00" not in l}


def regresion_de_los_tests_del_4b(destino: Path) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="aceptacion-h005-main-") as tmp:
        main = Path(tmp) / "main"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(main))
        sha = correr("git", "rev-parse", "origin/main").stdout.strip()
        correr("git", "-C", str(main), "checkout", "-q", "--detach", sha)
        correr("uv", "sync", "-q", cwd=main / "backend")
        antes = coleccion(main / "backend")
    if not antes:
        return ["no se pudieron coleccionar los tests del 4b en origin/main"]
    faltan = sorted(antes - coleccion(destino / "backend"))
    return [f"faltan {len(faltan)} tests del 4b, el primero: {faltan[0]}"] if faltan else []


def aceptacion_de_h004(destino: Path) -> list[str]:
    copiar_desde(H004_SHA, H004_CARPETA, destino / H004_DESTINO)
    codigo, casos, final = junit(destino / "backend", "tests/integracion/aceptacion_h004")
    if casos is None:
        return [f"la aceptación de H-004 no corrió (código {codigo}): {final}"]
    pasados = sum(x["estado"] == "pasa" for x in casos)
    if len(casos) != H004_ESPERADOS or pasados != H004_ESPERADOS:
        malos = [x for x in casos if x["estado"] != "pasa"]
        primero = f", el primero: {malos[0]['nombre']} ({malos[0]['mensaje']})" if malos else ""
        return [f"aceptación de H-004: {pasados} de {len(casos)} (se esperan {H004_ESPERADOS}){primero}"]
    return []


def barrido_de_migraciones(destino: Path) -> list[str]:
    backend = destino / "backend"
    lista = correr("rg", "-l", BARRIDO, "tests/integracion", "-g", "!**/aceptacion_h00*/**", cwd=backend,
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


def c20(destino: Path, casos: list[dict[str, str]] | None, sin_regresion: bool) -> None:
    faltas = []
    ciclo = [x for x in casos or [] if x["nombre"].startswith("test_c20_")]
    if not ciclo or any(x["estado"] != "pasa" for x in ciclo):
        faltas.append("el ciclo de la 0035 no pasa" + (f" ({ciclo[0]['mensaje']})" if ciclo else ""))
    ensayo = (destino / "infra/ci/ensayo-roles.sh")
    texto = ensayo.read_text() if ensayo.exists() else ""
    for tabla in TABLAS:
        if f"ALTER TABLE {tabla} OWNER TO" not in texto:
            faltas.append(f"el ensayo de roles no devuelve {tabla} al migrador")
    if sin_regresion:
        faltas.append("regresión no corrida (--sin-regresion)")
    else:
        faltas += regresion_de_los_tests_del_4b(destino)
        faltas += aceptacion_de_h004(destino)
        faltas += barrido_de_migraciones(destino)
    anotar("C20", not faltas, "; ".join(faltas) or
           "ciclo de la 0035, ensayo de roles, H-004 67/67, tests del 4b enteros y barrido de migraciones en verde")


def c21(destino: Path) -> None:
    def leer(ruta: str) -> str:
        p = destino / ruta
        return p.read_text() if p.exists() else ""

    faltas = []
    reglas = leer("knowledge-base/05_reglas_de_negocio.md")
    r09 = re.search(r"^## R09\b[^\n]*\n.*?(?=^## R\d\d\b|\Z)", reglas, flags=re.S | re.M)
    if r09 is None or not re.search(r"carga de saldo inicial", r09.group(0), flags=re.I) \
            or not re.search(r"firma del pedido", r09.group(0), flags=re.I):
        faltas.append("R09 no nombra la carga de saldo inicial y la firma del pedido")
    for ruta in ("knowledge-base/04_modelo_de_datos.md", "knowledge-base/08_arquitectura_propuesta.md"):
        texto = leer(ruta)
        for tabla in TABLAS:
            if tabla not in texto:
                faltas.append(f"{ruta.split('/')[-1]} no nombra {tabla}")
    glosario = leer("knowledge-base/11_glosario.md")
    for termino in ("carga de saldo inicial", "firma del pedido"):
        if not re.search(rf"\*\*{termino}\*\*", glosario, flags=re.I):
            faltas.append(f"el glosario no define «{termino}»")
    fichas = leer("knowledge-base/12_fichas_de_changes.md")
    ficha = re.search(r"^#{3,5} 4c\b[^\n]*\n.*?(?=^#{3,4} |\Z)", fichas, flags=re.S | re.M)
    if ficha is None or "H-005" not in ficha.group(0):
        faltas.append("la ficha del 4c no registra H-005")
    anotar("C21", not faltas, "; ".join(faltas) or "R09, 04, 08, 11 y la ficha del 4c al día")


def c22(destino: Path, casos: list[dict[str, str]] | None) -> None:
    candidatos = [destino / f"openspec/changes/{CAMBIO}/specs/{SPEC}/spec.md",
                  *sorted((destino / "openspec/changes/archive").glob(f"*-{CAMBIO}/specs/{SPEC}/spec.md")),
                  destino / f"openspec/specs/{SPEC}/spec.md"]
    texto = next((p.read_text() for p in candidatos if p.exists()), None)
    if texto is None:
        anotar("C22", False, f"no está la spec {SPEC}")
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
    anotar("C22", not faltas, "; ".join(faltas) or f"{len(titulos)} escenarios de {SPEC}, cada uno con su test en verde")


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--codigo", help=f"commit o ref del código (por defecto, {RAMA})")
    argumentos.add_argument("--local", action="store_true", help="tests del árbol de trabajo (sin congelar)")
    argumentos.add_argument("--sin-regresion", action="store_true", help="saltea H-004 y el barrido (C20 falla)")
    a = argumentos.parse_args()
    codigo = correr("git", "rev-parse", a.codigo or RAMA).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="aceptacion-h005-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
        correr("git", "-C", str(destino), "checkout", "-q", "--detach", codigo)
        copiar_tests(destino, a.local)
        correr("uv", "sync", "-q", cwd=destino / "backend")
        rc, casos, final = junit(destino / "backend", "tests/integracion/aceptacion_h005")
        if casos is None:
            anotar("TESTS", False, f"pytest no corrió los tests (código {rc}): {final}")
        else:
            criterios_de_tests(casos)
        c20(destino, casos, a.sin_regresion)
        c21(destino)
        c22(destino, casos)
    origen = "árbol de trabajo (SIN CONGELAR)" if a.local else f"aceptación {ACEPTACION_SHA[:7]}"
    print(f"H-005 · código {codigo[:7]} · {origen}")
    orden = {c: n for n, c in enumerate(["TESTS", *CRITERIOS_DE_TESTS, "C20", "C21", "C22"])}
    for criterio, ok, detalle in sorted(resultados, key=lambda r: orden.get(r[0], 99)):
        print(f"  H-005.{criterio:<5} {'PASA ' if ok else 'FALLA'}  {detalle}")
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
