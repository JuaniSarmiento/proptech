"""Aceptación de H-003: integrar el PR #6 `respaldos-2` (C-24, 1e, HIGH) a `main`.

Se corre desde la raíz del repo, con `gh` autenticado y Docker andando:

    python3 aceptacion/H-003/aceptar.py

Verifica sobre la fusión de `origin/main` con la cabeza del PR, sin tocar el árbol de trabajo:
  C01  la fusión no tiene conflictos; ninguna D ni L se repite; las decisiones del 1e son D-148 a
       D-150 y sus lecciones L-078 y L-079 (en `main`, D-144 a D-146 y L-068 y L-069 son de otros
       changes); las líneas que agrega el PR no nombran D-144 a D-146 ni L-068 ni L-069.
  C02  la cabeza del PR tiene todos sus checks en verde (al menos 6, con ensayo-roles) y un run del
       evento pull_request.
  C03  los 5 archivos de tests del change corren completos sobre la fusión: 108 esperados, 108
       pasados, ningún skip, falla ni error.
  C05  el change está archivado con sus specs sincronizadas, ninguna tarea sin marcar, CHANGES.md y la
       ficha del 1e lo dan por cerrado, CLAUDE.md == AGENTS.md.
  C06  la propuesta archivada lleva la firma de Juani del 11/11/2026 (D-094, D-111).
C04 (rompedor) y C07 (demo, con la conmutación real) no son ejecutables: se registran como evidencia
en HISTORIAS.md.

Sale con 0 sólo si todos los criterios pasan.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

PR = 6
BASE = "origin/main"
REPO = "JuaniSarmiento/proptech"
CAMBIO = "respaldos-2"
DECISIONES_DEL_PR = {
    148: '"14 copias" gana un piso por antigüedad',
    149: "F6 (la carrera del 503 sin su línea) se reprodujo",
    150: "Conmutar la aplicación a una base restaurada no vuelve",
}
LECCIONES_DEL_PR = {
    78: "Un doble falso de `docker` que matchea subcadenas",
    79: "Un test de `infra/` que depende de señales POSIX",
}
NUMEROS_VIEJOS = re.compile(r"D-14[4-6]\b|L-06[89]\b")
FIRMA = "**Firma: Juani Sarmiento, 2026-11-11.**"
TESTS = [
    "tests/infra/test_arrancar.py",
    "tests/infra/test_conmutar.py",
    "tests/infra/test_respaldos.py",
    "tests/integracion/test_respaldos_rol_real.py",
    "tests/unitarios/test_salud.py",
]
TESTS_ESPERADOS = 108
CHECKS_MINIMOS = 6

resultados: list[tuple[str, bool, str]] = []


def correr(*args: str, cwd: Path | None = None, chequear: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=chequear, stdin=subprocess.DEVNULL)


def anotar(criterio: str, ok: bool, detalle: str) -> None:
    resultados.append((criterio, ok, detalle))


def mostrar(arbol: str, ruta: str) -> str | None:
    r = correr("git", "show", f"{arbol}:{ruta}", chequear=False)
    return r.stdout if r.returncode == 0 else None


def rutas(arbol: str, prefijo: str) -> list[str]:
    return correr("git", "ls-tree", "-r", "--name-only", arbol, prefijo).stdout.split()


def archivo_del_cambio(arbol: str) -> str | None:
    dirs = {p.split("/")[3] for p in rutas(arbol, "openspec/changes/archive/") if p.split("/")[3].endswith(f"-{CAMBIO}")}
    return f"openspec/changes/archive/{sorted(dirs)[-1]}" if dirs else None


def c01(arbol: str | None, conflictos: str) -> None:
    if arbol is None:
        anotar("C01", False, f"la fusión con {BASE} tiene conflictos: {conflictos}")
        return
    faltas = []
    textos = {
        "D": mostrar(arbol, "knowledge-base/09_decisiones_y_supuestos.md") or "",
        "L": mostrar(arbol, "knowledge-base/15_lecciones.md") or "",
    }
    for letra, texto in textos.items():
        numeros = [int(n) for n in re.findall(rf"^## {letra}-(\d+) ", texto, flags=re.M)]
        repetidas = sorted(n for n, c in Counter(numeros).items() if c > 1)
        if repetidas:
            faltas.append(f"{letra} repetidas: {repetidas}")
    for letra, esperadas in (("D", DECISIONES_DEL_PR), ("L", LECCIONES_DEL_PR)):
        for numero, titulo in esperadas.items():
            m = re.search(rf"^## {letra}-(\d+) · {re.escape(titulo)}", textos[letra], flags=re.M)
            if m is None:
                faltas.append(f"falta la {letra} «{titulo[:30]}…»")
            elif int(m.group(1)) != numero:
                faltas.append(f"«{titulo[:30]}…» es {letra}-{m.group(1)}, se espera {letra}-{numero:03d}")
    agregadas = [l for l in correr("git", "diff", BASE, arbol).stdout.splitlines()
                 if l.startswith("+") and not l.startswith("+++") and NUMEROS_VIEJOS.search(l)]
    if agregadas:
        faltas.append(f"{len(agregadas)} líneas agregadas nombran D-144 a D-146 o L-068/L-069, la primera: {agregadas[0][:100]}")
    anotar("C01", not faltas, "; ".join(faltas) or "sin conflictos; D-148 a D-150 y L-078, L-079; ninguna D ni L repetida")


def c02(cabeza: str) -> None:
    datos = json.loads(correr("gh", "api", f"repos/{REPO}/commits/{cabeza}/check-runs").stdout)
    corridas = datos["check_runs"]
    malas = [f"{c['name']}={c['status']}/{c['conclusion']}" for c in corridas
             if c["status"] != "completed" or c["conclusion"] not in ("success", "skipped")]
    runs = json.loads(correr("gh", "run", "list", "--repo", REPO, "--commit", cabeza, "--event",
                             "pull_request", "--json", "conclusion").stdout)
    if len(corridas) < CHECKS_MINIMOS:
        anotar("C02", False, f"{len(corridas)} checks sobre {cabeza[:7]}, se esperan al menos {CHECKS_MINIMOS}")
    elif malas:
        anotar("C02", False, f"checks que no están en verde: {malas}")
    elif not any(r["conclusion"] == "success" for r in runs):
        anotar("C02", False, f"ningún run del evento pull_request en verde sobre {cabeza[:7]}")
    else:
        anotar("C02", True, f"{len(corridas)} checks en verde sobre {cabeza[:7]}")


def c03(destino: Path) -> None:
    backend = destino / "backend"
    correr("uv", "sync", "-q", cwd=backend)
    with tempfile.TemporaryDirectory(prefix="aceptacion-h003-junit-") as tmp:
        informe = Path(tmp) / "junit.xml"
        corrida = correr("uv", "run", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={informe}", *TESTS,
                         cwd=backend, chequear=False)
        # 0 = todo pasó, 1 = hubo fallas; cualquier otro código es que pytest no llegó a correr.
        if corrida.returncode not in (0, 1) or not informe.exists():
            final = (corrida.stdout + corrida.stderr).strip().splitlines()[-3:]
            anotar("C03", False, f"pytest no corrió los tests (código {corrida.returncode}): {' | '.join(final)}")
            return
        raiz = ET.parse(informe).getroot()
        suite = raiz if raiz.tag == "testsuite" else raiz.find("testsuite")
        assert suite is not None
        total, fallas, errores, skips = (int(suite.get(k, "0")) for k in ("tests", "failures", "errors", "skipped"))
    pasados = total - fallas - errores - skips
    detalle = f"{TESTS_ESPERADOS} esperados; {total} ejecutados, {pasados} pasados, {fallas} fallas, {errores} errores, {skips} skips"
    anotar("C03", total == TESTS_ESPERADOS and pasados == TESTS_ESPERADOS, detalle)


def c05_c06(arbol: str | None) -> None:
    if arbol is None:
        anotar("C05", False, "no hay fusión que revisar (C01)")
        anotar("C06", False, "no hay fusión que revisar (C01)")
        return
    faltas = []
    archivo = archivo_del_cambio(arbol)
    if archivo is None:
        faltas.append(f"no hay openspec/changes/archive/*-{CAMBIO}")
    if rutas(arbol, f"openspec/changes/{CAMBIO}/"):
        faltas.append(f"sigue el change activo openspec/changes/{CAMBIO}")
    if archivo is not None:
        for spec in (p for p in rutas(arbol, f"{archivo}/specs/") if p.endswith("spec.md")):
            capacidad = spec.split("/")[-2]
            principal = mostrar(arbol, f"openspec/specs/{capacidad}/spec.md") or ""
            for req in re.findall(r"^### Requirement: (.+)$", mostrar(arbol, spec) or "", flags=re.M):
                if f"### Requirement: {req}" not in principal:
                    faltas.append(f"openspec/specs/{capacidad} no tiene «{req[:40]}»")
        abiertas = re.findall(r"^\s*- \[ \] (\S+)", mostrar(arbol, f"{archivo}/tasks.md") or "", flags=re.M)
        if abiertas:
            faltas.append(f"tareas sin marcar: {abiertas}")
    if mostrar(arbol, "CLAUDE.md") != mostrar(arbol, "AGENTS.md"):
        faltas.append("CLAUDE.md y AGENTS.md difieren")
    if "✅ 1e respaldos-2" not in (mostrar(arbol, "CHANGES.md") or ""):
        faltas.append("CHANGES.md no marca el 1e como hecho")
    if "### 1e · `respaldos-2`" not in (mostrar(arbol, "knowledge-base/12_fichas_de_changes.md") or ""):
        faltas.append("no está la ficha del 1e")
    anotar("C05", not faltas, "; ".join(faltas[:4]) or "archivado, specs sincronizadas, tareas marcadas, CHANGES y ficha al día, CLAUDE == AGENTS")
    propuesta = mostrar(arbol, f"{archivo}/proposal.md") if archivo else None
    if propuesta is None:
        anotar("C06", False, "no hay proposal.md del change archivado")
    else:
        anotar("C06", FIRMA in propuesta, "firma de Juani del 11/11/2026 en la propuesta" if FIRMA in propuesta
               else "la propuesta archivada no tiene la firma de Juani del 11/11/2026")


def main() -> int:
    correr("git", "fetch", "-q", "origin")
    cabeza = json.loads(correr("gh", "pr", "view", str(PR), "--repo", REPO, "--json", "headRefOid").stdout)["headRefOid"]
    fusion = correr("git", "merge-tree", "--write-tree", "--name-only", BASE, cabeza, chequear=False)
    lineas = fusion.stdout.split("\n")
    arbol = lineas[0].strip() if fusion.returncode == 0 else None
    conflictos = ", ".join(l for l in lineas[1:] if l and not l.startswith(("Auto", "CONFLICT")))
    c01(arbol, conflictos)
    c02(cabeza)
    c05_c06(arbol)
    if arbol is None:
        anotar("C03", False, "no hay fusión sobre la que correr los tests (C01)")
    else:
        base = correr("git", "rev-parse", BASE).stdout.strip()
        commit = correr("git", "commit-tree", arbol, "-p", base, "-p", cabeza, "-m", "aceptacion H-003").stdout.strip()
        # Un clon y no un worktree: los scripts de infra escriben evidencia en `.git/`.
        with tempfile.TemporaryDirectory(prefix="aceptacion-h003-") as tmp:
            destino = Path(tmp) / "arbol"
            correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
            correr("git", "-C", str(destino), "checkout", "-q", "--detach", commit)
            c03(destino)
    print(f"H-003 · PR #{PR} · cabeza {cabeza[:7]} sobre {BASE}")
    for criterio, ok, detalle in sorted(resultados):
        print(f"  H-003.{criterio}  {'PASA ' if ok else 'FALLA'}  {detalle}")
    print("  H-003.C04  manual  rompedor de otra familia de modelo: evidencia en HISTORIAS.md")
    print("  H-003.C07  manual  demo con la conmutación real: evidencia en HISTORIAS.md")
    return 0 if all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
