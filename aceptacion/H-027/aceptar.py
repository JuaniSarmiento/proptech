"""Aceptación de H-027: la lectura de la morosidad (change 10a `morosidad`, parte 1, HIGH; HU-A8, R20, D-167).
Criterios en HISTORIAS.md, sección H-027. Sin chequeo de CI (D-154).

    python3 aceptacion/H-027/aceptar.py --sin-regresion    # por historia (la regresión, al cierre)
    python3 aceptacion/H-027/aceptar.py --local            # tests del árbol de trabajo (sin congelar)

  C01 a C06, N01 a N06  cada test lleva su criterio en el nombre.
  C07  la KB (K01 a K03) y la ficha 10a con H-027; los estructurales y, al cierre, H-004 a H-026 y el barrido.
  SPEC los escenarios de la spec `morosidad` que cubre esta historia, cada uno con su test en verde.
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

RAMA = "10a-morosidad"
CAMBIO = "morosidad"
#: El commit que congela esta aceptación (lo aprueba Juani). Vacío mientras se escribe.
ACEPTACION_SHA = "3265551dc584115cf5da838ba9df3c9087eceaf3"
CARPETA = "aceptacion/H-027/tests"
DESTINO = "backend/tests/integracion/aceptacion_h027"
TESTS_ESPERADOS = 25
CRITERIOS_DE_TESTS = [*(f"C{n:02d}" for n in range(1, 7)), *(f"N{n:02d}" for n in range(1, 7))]
SPEC = "morosidad"
#: Los escenarios de la spec que cubre H-027 (los demás son de H-028 y H-029).
ESCENARIOS = (
    "Moroso crítico y unidad al día",
    "Deuda pagada en partes",
    "Una sola liquidación vencida",
    "Sólo queda el interés de la más vieja",
    "El vecino no ve la morosidad",
    "El libro queda igual",
)
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
#: Tests de aceptaciones anteriores atados a su momento (L-082): sólo se perdonan con ese mensaje exacto.
CADUCOS = {
    "test_c17_la_0034_sube_y_baja_en_el_ciclo_de_devolucion": "la cabeza no es la 0034",
    "test_c20_la_0035_sube_y_baja_en_el_ciclo_de_devolucion": "la cabeza no es la 0035",
}
#: Tests que pasan antes de construir: el comportamiento ya existe (regresión).
NACEN_VERDES: dict[str, str] = {
    "test_n01_fuera_del_alcance_da_404": "guarda: sin la ruta ya da 404; construida, tiene que seguir en 404",
    "test_n01_un_edificio_de_otra_administracion_da_404": "guarda: ídem, con el edificio de otra administración",
}

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
    with tempfile.TemporaryDirectory(prefix="aceptacion-h027-junit-") as tmp:
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


def c07(destino: Path, sin_regresion: bool) -> None:
    faltas = []
    r20 = seccion(leer(destino, "knowledge-base/05_reglas_de_negocio.md"), r"R20 ·")
    if "/morosidad" not in r20 or "vencida_desde" not in r20 or "intereses_al" not in r20:
        faltas.append("K01: R20 no dice dónde vive el listado (`/morosidad`) con `vencida_desde` e `intereses_al`")
    d167 = seccion(leer(destino, "knowledge-base/09_decisiones_y_supuestos.md"), r"D-167 ·")
    if "morosidad" not in d167.lower():
        faltas.append("K02: no está D-167 con los acuerdos de la morosidad")
    if "ver_morosidad" not in leer(destino, "knowledge-base/03_actores_y_roles.md"):
        faltas.append("K03: `03_actores_y_roles.md` no nombra `ver_morosidad`")
    if "H-027" not in seccion(leer(destino, "knowledge-base/12_fichas_de_changes.md"), r"10a ·"):
        faltas.append("la ficha 10a no registra H-027")
    faltas += estructurales(destino)
    if sin_regresion:
        faltas.append("regresión no corrida (--sin-regresion)")
    else:
        previas = ("H-005", "H-006", "H-007", "H-008", "H-009", "H-010", "H-011", "H-012", "H-013", "H-014", "H-016",
                   "H-015", "H-017", "H-018", "H-019", "H-020", "H-021", "H-022", "H-023", "H-024", "H-025", "H-026")
        for historia, sha, esperados in (H004, *(congelada(h) for h in previas)):
            faltas += aceptacion_previa(destino, historia, sha, esperados)
        faltas += barrido_de_migraciones(destino)
    anotar("C07", not faltas, "; ".join(faltas) or "K01 a K03, ficha 10a, estructurales, H-004 a H-026 y barrido")


def spec(destino: Path, casos: list[dict[str, str]]) -> None:
    candidatos = [destino / f"openspec/changes/{CAMBIO}/specs/{SPEC}/spec.md",
                  *sorted((destino / "openspec/changes/archive").glob(f"*-{CAMBIO}/specs/{SPEC}/spec.md")),
                  destino / f"openspec/specs/{SPEC}/spec.md"]
    texto = next((p.read_text() for p in candidatos if p.exists()), None)
    if texto is None:
        anotar("SPEC", False, f"no está la spec {SPEC}")
        return
    titulos = set(re.findall(r"^#### Scenario: (.+?)\s*$", texto, flags=re.M))
    faltan_en_spec = [e for e in ESCENARIOS if e not in titulos]
    verdes = {x["nombre"].split("[")[0] for x in casos if x["estado"] == "pasa"}
    malos = {x["nombre"].split("[")[0] for x in casos if x["estado"] != "pasa"}
    cubiertos: dict[str, set[str]] = defaultdict(set)
    for archivo in (destino / DESTINO).glob("test_*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text())):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                for titulo in re.findall(r"Escenario: (.+)", ast.get_docstring(nodo) or ""):
                    cubiertos[titulo.strip()].add(nodo.name)
    sin_test = [t for t in ESCENARIOS if not cubiertos.get(t)]
    sin_verde = [t for t in ESCENARIOS if cubiertos.get(t) and (not cubiertos[t] & verdes or cubiertos[t] & malos)]
    faltas = []
    if faltan_en_spec:
        faltas.append(f"{len(faltan_en_spec)} escenarios no están en la spec, el primero «{faltan_en_spec[0]}»")
    if sin_test:
        faltas.append(f"{len(sin_test)} escenarios sin test, el primero «{sin_test[0]}»")
    if sin_verde:
        faltas.append(f"{len(sin_verde)} escenarios con tests que no pasan, el primero «{sin_verde[0]}»")
    anotar("SPEC", not faltas, "; ".join(faltas) or f"{len(ESCENARIOS)} escenarios de {SPEC}, cada uno en verde")


def es_asercion(caso: dict[str, str]) -> bool:
    m = caso["mensaje"]
    return caso["estado"] == "falla" and m.startswith(("AssertionError", "assert", "Failed"))


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--codigo", help=f"commit o ref del código (por defecto, {RAMA})")
    argumentos.add_argument("--local", action="store_true", help="tests del árbol de trabajo (sin congelar)")
    argumentos.add_argument("--sin-regresion", action="store_true", help="saltea H-004 a H-026 y el barrido")
    a = argumentos.parse_args()
    codigo = correr("git", "rev-parse", a.codigo or RAMA).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="aceptacion-h027-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
        correr("git", "-C", str(destino), "checkout", "-q", "--detach", codigo)
        copiar_tests(destino, a.local)
        correr("uv", "sync", "-q", cwd=destino / "backend")
        rc, casos, final = junit(destino / "backend", "tests/integracion/aceptacion_h027")
        if casos is None:
            anotar("TESTS", False, f"pytest no corrió los tests (código {rc}): {final}")
            casos = []
        criterios_de_tests(casos)
        c07(destino, a.sin_regresion)
        spec(destino, casos)
    origen = "árbol de trabajo (SIN CONGELAR)" if a.local else f"aceptación {ACEPTACION_SHA[:7]}"
    print(f"H-027 · código {codigo[:7]} · {origen}")
    orden = {c: n for n, c in enumerate(["TESTS", *CRITERIOS_DE_TESTS, "C07", "SPEC"])}
    for criterio, ok, detalle in sorted(resultados, key=lambda r: orden.get(r[0], 99)):
        print(f"  H-027.{criterio:<5} {'PASA ' if ok else 'FALLA'}  {detalle}")
    if casos:
        rojos = [x for x in casos if x["estado"] != "pasa"]
        no_asercion = [x for x in rojos if not es_asercion(x)]
        print(f"  rojos ({len(rojos)}); que no son por aserción ({len(no_asercion)}): "
              + ", ".join(f"{x['nombre']} [{x['estado']}: {x['mensaje'][:110]}]" for x in no_asercion))
    return 0 if resultados and all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
