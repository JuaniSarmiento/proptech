"""Aceptación de H-008: borrador de saldos y comparación (change 5 `importacion-desde-excel`, parte 2,
CRITICAL). Criterios en HISTORIAS.md, sección H-008. Sin chequeo de CI (D-154: el CI corre al cerrar el change).

Se corre desde la raíz del repo, con `uv`, Docker (los tests de backend levantan su propio PostgreSQL con
testcontainers), Node con `corepack` y el Chromium de Playwright instalado:

    python3 aceptacion/H-008/aceptar.py                    # código: la rama del 5
    python3 aceptacion/H-008/aceptar.py --codigo <ref>     # otro commit
    python3 aceptacion/H-008/aceptar.py --local            # tests del árbol de trabajo, no del SHA
                                                           # congelado: sólo para escribirla
    python3 aceptacion/H-008/aceptar.py --sin-regresion    # saltea las aceptaciones de H-004 a H-007 y
                                                           # el barrido de migraciones (C16 queda en FALLA)
    python3 aceptacion/H-008/aceptar.py --sin-navegador    # saltea los e2e (C12 y C15 quedan en FALLA)

Qué hace, sin tocar el árbol de trabajo: clona el repo con `--shared` (no un worktree: los scripts de
infra escriben en `.git/`), deja el clon en el commit del código, copia los tests de la aceptación
**desde el SHA congelado** (`ACEPTACION_SHA`): los de backend a `backend/tests/integracion/aceptacion_h008/`
(usan `conftest.py` y las fixtures del repo) y los de navegador a `web/e2e/`. Corre pytest y Playwright
con `--junitxml` / `--reporter=junit`. Playwright corre como lo hace el job `web` (build de Next, API falsa
y `next start`), con los mismos pasos que `infra/ci/test-web-navegador.sh` pero sin llamar a ese script
(este script nunca corre `infra/ci/*.sh`), en puertos propios.

  C01 a C15  cada test lleva su criterio en el nombre (`test_c13_…`) o, en Playwright, en el título
             (`C12 · …`); un criterio pasa si todos sus tests corren y pasan, y la corrida entera tiene
             los `TESTS_ESPERADOS` y los `E2E_ESPERADOS`, sin skips ni errores.
  C16  los tests `test_c16_*` (ciclo de la 0037, RLS forzada, sólo agregar, vocabulario y matriz)
       pasan; los tests de fronteras, rutas protegidas y vocabulario del repo pasan; las aceptaciones de
       H-004 a H-007 (desde sus SHA congelados) siguen en verde; los tests que bajan o restauran
       migraciones pasan; el ensayo de roles devuelve `aceptacion_de_diferencias`.
  C17  la base de conocimiento: R09 con el borrador, el control y la aceptación; las tres tablas en 04
       y 08; el glosario con el borrador de saldos y el control; la ficha 5 con H-008.
  C18  cada escenario de la spec `borrador-de-saldos` está en el docstring (`Escenario: <título>`)
       de un test que corrió y pasó.

Sale con 0 sólo si todos los criterios pasan.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

RAMA = "change/importacion-desde-excel"
CAMBIO = "importacion-desde-excel"
#: El commit que congela esta aceptación (lo aprueba Juani). Vacío mientras se escribe.
ACEPTACION_SHA = "f214893eb656d466043716aff3a085d9e0a482ec"
CARPETA = "aceptacion/H-008/tests"
CARPETA_E2E = "aceptacion/H-008/e2e"
DESTINO = "backend/tests/integracion/aceptacion_h008"
DESTINO_E2E = "web/e2e"
TESTS_ESPERADOS = 58
E2E_ESPERADOS = 4
CRITERIOS_DE_TESTS = [f"C{n:02d}" for n in range(1, 16)]
SPEC = "borrador-de-saldos"
#: Los tests que bajan o restauran migraciones (L-064, L-083).
BARRIDO = r"downgrade|\.migrar\(|alembic.*(up|down)grade|pg_restore"
#: Los tests estructurales del repo que esta historia toca (C16).
ESTRUCTURALES = (
    "tests/unitarios/test_fronteras_de_modulos.py",
    "tests/integracion/test_rutas_protegidas.py",
    "tests/integracion/test_vocabulario_configuracion.py",
)
#: Aceptaciones anteriores que tienen que seguir en verde (C16).
H004 = ("H-004", "d2da37ef509cfb88ef62d5e12b5d4b3ec18d270e", 67)
#: Tests de aceptaciones anteriores atados a su momento (L-082): fijan la cabeza de alembic en su
#: migración, que una migración posterior supera. Sólo se perdonan con ese mensaje exacto; el ciclo de
#: cada migración lo vigila su propio test de ciclo (decisión del orquestador, 11/11/2026).
CADUCOS = {
    "test_c17_la_0034_sube_y_baja_en_el_ciclo_de_devolucion": "la cabeza no es la 0034",
    "test_c20_la_0035_sube_y_baja_en_el_ciclo_de_devolucion": "la cabeza no es la 0035",
}
#: Tests que pasan antes de construir: el comportamiento ya existe (regresión).
NACEN_VERDES: dict[str, str] = {}
PUERTO_API_FALSA = "4181"
PUERTO_WEB = "3181"
PNPM = "pnpm@12.10.1"

resultados: list[tuple[str, bool, str]] = []


def correr(*args: str, cwd: Path | None = None, chequear: bool = True,
           entorno: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=chequear,
                          stdin=subprocess.DEVNULL, env=entorno)


def anotar(criterio: str, ok: bool, detalle: str) -> None:
    resultados.append((criterio, ok, detalle))


def mostrar(arbol: str, ruta: str) -> str | None:
    r = correr("git", "show", f"{arbol}:{ruta}", chequear=False)
    return r.stdout if r.returncode == 0 else None


def copiar_desde(sha: str, carpeta: str, destino: Path, sufijos: tuple[str, ...] = (".py",)) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in correr("git", "ls-tree", "--name-only", f"{sha}:{carpeta}").stdout.split():
        if nombre.endswith(sufijos):
            (destino / nombre).write_text(mostrar(sha, f"{carpeta}/{nombre}") or "")


def copiar_tests(destino: Path, local: bool) -> None:
    if local:
        (destino / DESTINO).mkdir(parents=True)
        for f in Path(CARPETA).glob("*.py"):
            shutil.copy(f, destino / DESTINO / f.name)
        for f in Path(CARPETA_E2E).glob("*.spec.ts"):
            shutil.copy(f, destino / DESTINO_E2E / f.name)
        return
    if not ACEPTACION_SHA:
        sys.exit("ACEPTACION_SHA vacío: la aceptación no está congelada (usar --local para escribirla)")
    copiar_desde(ACEPTACION_SHA, CARPETA, destino / DESTINO)
    copiar_desde(ACEPTACION_SHA, CARPETA_E2E, destino / DESTINO_E2E, (".spec.ts",))


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
    with tempfile.TemporaryDirectory(prefix="aceptacion-h008-junit-") as tmp:
        informe = Path(tmp) / "junit.xml"
        corrida = correr("uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
                         f"--junitxml={informe}", *objetivos, cwd=backend, chequear=False)
        final = " | ".join((corrida.stdout + corrida.stderr).strip().splitlines()[-3:])
        if corrida.returncode not in (0, 1) or not informe.exists():
            return corrida.returncode, None, final
        return corrida.returncode, casos_de_junit(informe), final


#: Los pasos de `infra/ci/test-web-navegador.sh`, sin llamar a ese script: build, API falsa, `next
#: start` y Playwright sólo con los archivos de la aceptación, en puertos propios.
_NAVEGADOR = r"""
set -euo pipefail
set -m
export PROPTECH_PUERTO_API_FALSA="$1" PROPTECH_URL_API_INTERNA="http://127.0.0.1:$1"
export PROPTECH_URL_WEB="http://127.0.0.1:$2"
PID_API=""; PID_WEB=""
limpiar() {
  [ -n "$PID_WEB" ] && kill -- "-$PID_WEB" 2>/dev/null || true
  [ -n "$PID_API" ] && kill -- "-$PID_API" 2>/dev/null || true
}
trap limpiar EXIT
esperar() {
  local n=0
  until (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; do
    n=$((n + 1)); [ "$n" -ge 120 ] && { echo "nadie contesta en :$1" >&2; exit 3; }; sleep 0.5
  done
}
corepack "$3" install --frozen-lockfile --prefer-offline >/dev/null
source e2e/configurar-clerk.sh
corepack "$3" build >/dev/null
corepack "$3" exec tsx e2e/api-falsa.ts >/dev/null 2>&1 &
PID_API=$!
esperar "$1"
PORT="$2" corepack "$3" start >/dev/null 2>&1 &
PID_WEB=$!
esperar "$2"
shift 3
PLAYWRIGHT_JUNIT_OUTPUT_NAME="$JUNIT_E2E" corepack pnpm@12.10.1 exec playwright test --reporter=junit "$@"
"""


def navegador(destino: Path) -> tuple[int, list[dict[str, str]] | None, str]:
    archivos = sorted(f"e2e/{p.name}" for p in (destino / DESTINO_E2E).glob("aceptacion-h008-*.spec.ts"))
    if not archivos:
        return 0, None, "no hay e2e de la aceptación en el clon"
    with tempfile.TemporaryDirectory(prefix="aceptacion-h008-e2e-") as tmp:
        informe = Path(tmp) / "junit.xml"
        entorno = {**os.environ, "JUNIT_E2E": str(informe)}
        corrida = correr("bash", "-c", _NAVEGADOR, "navegador", PUERTO_API_FALSA, PUERTO_WEB, PNPM, *archivos,
                         cwd=destino / "web", chequear=False, entorno=entorno)
        final = " | ".join((corrida.stdout + corrida.stderr).strip().splitlines()[-4:])
        if not informe.exists():
            return corrida.returncode, None, final
        return corrida.returncode, casos_de_junit(informe), final


def criterios_del_test(nombre: str) -> list[str]:
    m = re.match(r"test_((?:c\d\d_)+)", nombre)
    if m:
        return [f"C{t[1:]}" for t in m.group(1).split("_") if t]
    return re.findall(r"\b(C\d\d) ·", nombre)


def criterios_de_tests(casos: list[dict[str, str]], e2e: list[dict[str, str]] | None) -> None:
    todos = [*casos, *(e2e or [])]
    por_criterio: dict[str, list[dict[str, str]]] = defaultdict(list)
    for caso in todos:
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
    for nombre, lista, esperados in (("TESTS", casos, TESTS_ESPERADOS), ("E2E", e2e or [], E2E_ESPERADOS)):
        pasados = sum(x["estado"] == "pasa" for x in lista)
        conteo = {e: sum(x["estado"] == e for x in lista) for e in ("falla", "error", "skip")}
        anotar(nombre, len(lista) == esperados and pasados == esperados,
               f"{esperados} esperados; {len(lista)} ejecutados, {pasados} pasados, {conteo['falla']} fallas, "
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


def estructurales(destino: Path) -> list[str]:
    codigo, casos, final = junit(destino / "backend", *ESTRUCTURALES)
    if casos is None:
        return [f"los tests estructurales no corrieron (código {codigo}): {final}"]
    malos = [x for x in casos if x["estado"] not in ("pasa", "skip")]
    return [f"tests estructurales: {len(malos)} no pasan, el primero: {malos[0]['nombre']} "
            f"({malos[0]['mensaje']})"] if malos else []


def c16(destino: Path, casos: list[dict[str, str]] | None, sin_regresion: bool) -> None:
    faltas = []
    propios = [x for x in casos or [] if x["nombre"].startswith("test_c16_")]
    malos = [x for x in propios if x["estado"] != "pasa"]
    if not propios or malos:
        faltas.append("tests de esquema y migración de la 0037" +
                      (f": {malos[0]['nombre']} ({malos[0]['mensaje']})" if malos else " no corrieron"))
    ensayo = destino / "infra/ci/ensayo-roles.sh"
    if "ALTER TABLE aceptacion_de_diferencias OWNER TO" not in (ensayo.read_text() if ensayo.exists() else ""):
        faltas.append("el ensayo de roles no devuelve aceptacion_de_diferencias al migrador (L-083)")
    faltas += estructurales(destino)
    if sin_regresion:
        faltas.append("regresión no corrida (--sin-regresion)")
    else:
        for historia, sha, esperados in (H004, congelada("H-005"), congelada("H-006"), congelada("H-007")):
            faltas += aceptacion_previa(destino, historia, sha, esperados)
        faltas += barrido_de_migraciones(destino)
    anotar("C16", not faltas, "; ".join(faltas) or
           "0037 con su ciclo, RLS, sólo agregar y vocabulario; ensayo de roles; estructurales, H-004 a H-007 "
           "y barrido de migraciones en verde")


def seccion(texto: str, encabezado: str) -> str:
    m = re.search(rf"^(#+) {encabezado}[^\n]*\n.*?(?=^\1 |\Z)", texto, flags=re.S | re.M)
    return m.group(0) if m else ""


def c17(destino: Path) -> None:
    def leer(ruta: str) -> str:
        p = destino / "knowledge-base" / ruta
        return p.read_text() if p.exists() else ""

    faltas = []
    r09 = seccion(leer("05_reglas_de_negocio.md"), r"R09\b")
    for palabra in ("borrador", "control", "acept"):
        if not re.search(palabra, r09, flags=re.I):
            faltas.append(f"R09 no nombra {palabra!r}")
    for ruta in ("04_modelo_de_datos.md", "08_arquitectura_propuesta.md"):
        texto = leer(ruta)
        for tabla in ("fila_de_saldo_importada", "control_de_saldo", "aceptacion_de_diferencias"):
            if tabla not in texto:
                faltas.append(f"{ruta} no nombra {tabla}")
    glosario = leer("11_glosario.md")
    for termino in ("Borrador de saldos", "Control"):
        if not re.search(rf"\*\*{termino}", glosario, flags=re.I):
            faltas.append(f"el glosario no define «{termino}»")
    if "H-008" not in seccion(leer("12_fichas_de_changes.md"), r"5 ·"):
        faltas.append("la ficha 5 no registra H-008")
    anotar("C17", not faltas, "; ".join(faltas) or "R09, 04, 08, 11 y la ficha 5 al día")


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


def es_asercion(caso: dict[str, str]) -> bool:
    m = caso["mensaje"]
    return caso["estado"] == "falla" and (m.startswith(("AssertionError", "assert", "Failed")) or "expect(" in m)


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--codigo", help=f"commit o ref del código (por defecto, {RAMA})")
    argumentos.add_argument("--local", action="store_true", help="tests del árbol de trabajo (sin congelar)")
    argumentos.add_argument("--sin-regresion", action="store_true", help="saltea H-004 a H-007 y el barrido")
    argumentos.add_argument("--sin-navegador", action="store_true", help="saltea los e2e de Playwright")
    a = argumentos.parse_args()
    codigo = correr("git", "rev-parse", a.codigo or RAMA).stdout.strip()
    e2e: list[dict[str, str]] | None = None
    with tempfile.TemporaryDirectory(prefix="aceptacion-h008-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
        correr("git", "-C", str(destino), "checkout", "-q", "--detach", codigo)
        copiar_tests(destino, a.local)
        correr("uv", "sync", "-q", cwd=destino / "backend")
        rc, casos, final = junit(destino / "backend", "tests/integracion/aceptacion_h008")
        if casos is None:
            anotar("TESTS", False, f"pytest no corrió los tests (código {rc}): {final}")
            casos = []
        if not a.sin_navegador:
            rc_e2e, e2e, final_e2e = navegador(destino)
            if e2e is None:
                print(f"  Playwright no dejó informe (código {rc_e2e}): {final_e2e}")
        criterios_de_tests(casos, e2e)
        c16(destino, casos, a.sin_regresion)
        c17(destino)
        c18(destino, casos)
    origen = "árbol de trabajo (SIN CONGELAR)" if a.local else f"aceptación {ACEPTACION_SHA[:7]}"
    print(f"H-008 · código {codigo[:7]} · {origen}")
    orden = {c: n for n, c in enumerate(["TESTS", "E2E", *CRITERIOS_DE_TESTS, "C16", "C17", "C18"])}
    for criterio, ok, detalle in sorted(resultados, key=lambda r: orden.get(r[0], 99)):
        print(f"  H-008.{criterio:<5} {'PASA ' if ok else 'FALLA'}  {detalle}")
    todos = [*casos, *(e2e or [])]
    if todos:
        rojos = [x for x in todos if x["estado"] != "pasa"]
        no_asercion = [x for x in rojos if not es_asercion(x)]
        print(f"  rojos ({len(rojos)}); que no son por aserción ({len(no_asercion)}): "
              + ", ".join(f"{x['nombre']} [{x['estado']}: {x['mensaje'][:110]}]" for x in no_asercion))
    return 0 if resultados and all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
