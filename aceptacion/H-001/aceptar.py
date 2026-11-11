"""Aceptación de H-001: integrar el PR #7 `ejemplo-robusto` (C-27) a `main`.

Se corre desde la raíz del repo, con `gh` autenticado y Docker andando:

    python3 aceptacion/H-001/aceptar.py

Verifica sobre la fusión de `origin/main` con la cabeza del PR, sin tocar el árbol de trabajo:
  C01  la fusión no tiene conflictos; ninguna D se repite en 09 y D-145 va antes que D-146.
  C02  la cabeza del PR tiene todos sus checks en verde y un run del evento pull_request.
  C03  los tres archivos de tests del change corren completos sobre la fusión: 258 esperados,
       258 pasados, ningún skip, falla ni error.
  C05  el change está archivado, CHANGES.md y la ficha lo dan por cerrado, CLAUDE.md == AGENTS.md.
C06 (demo) no es ejecutable: se registra como evidencia en HISTORIAS.md. C04 (revisión
independiente) se sacó el 11/11/2026: un LOW no lleva revisión aparte (D-146).

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

PR = 7
BASE = "origin/main"
REPO = "JuaniSarmiento/proptech"
ARCHIVO = "openspec/changes/archive/2026-11-04-ejemplo-robusto"
ACTIVO = "openspec/changes/ejemplo-robusto"
TESTS = [
    "tests/integracion/test_ejemplo_casos_de_uso.py",
    "tests/integracion/test_arranque_tablas_protegidas.py",
    "tests/unitarios/test_puntos_de_entrada_prohibidos.py",
]
TESTS_ESPERADOS = 258
CHECKS_MINIMOS = 5

resultados: list[tuple[str, bool, str]] = []


def correr(*args: str, cwd: Path | None = None, chequear: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=chequear)


def anotar(criterio: str, ok: bool, detalle: str) -> None:
    resultados.append((criterio, ok, detalle))


def mostrar(arbol: str, ruta: str) -> str | None:
    r = correr("git", "show", f"{arbol}:{ruta}", chequear=False)
    return r.stdout if r.returncode == 0 else None


def c01(arbol: str | None, conflictos: str) -> None:
    if arbol is None:
        anotar("C01", False, f"la fusión con {BASE} tiene conflictos: {conflictos}")
        return
    decisiones = mostrar(arbol, "knowledge-base/09_decisiones_y_supuestos.md") or ""
    numeros = [int(n) for n in re.findall(r"^## D-(\d+) ", decisiones, flags=re.M)]
    repetidas = sorted(n for n, c in Counter(numeros).items() if c > 1)
    if repetidas:
        anotar("C01", False, f"D repetidas en 09: {repetidas}")
    elif 145 not in numeros or 146 not in numeros:
        anotar("C01", False, "falta D-145 o D-146 en 09")
    elif numeros.index(145) > numeros.index(146):
        anotar("C01", False, "D-145 quedó después de D-146")
    else:
        anotar("C01", True, f"sin conflictos; {len(numeros)} decisiones, ninguna repetida")


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


def c03(arbol: str | None, cabeza: str) -> None:
    if arbol is None:
        anotar("C03", False, "no hay fusión sobre la que correr los tests (C01)")
        return
    base = correr("git", "rev-parse", BASE).stdout.strip()
    fusion = correr("git", "commit-tree", arbol, "-p", base, "-p", cabeza, "-m", "aceptacion H-001").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="aceptacion-h001-") as tmp:
        destino = Path(tmp) / "arbol"
        correr("git", "worktree", "add", "--detach", str(destino), fusion)
        try:
            backend = destino / "backend"
            correr("uv", "sync", "-q", cwd=backend)
            informe = Path(tmp) / "junit.xml"
            corrida = correr("uv", "run", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={informe}",
                             *TESTS, cwd=backend, chequear=False)
            # 0 = todo pasó, 1 = hubo fallas; cualquier otro código es que pytest no llegó a correr
            # (interrumpido, error interno, uso incorrecto o nada recolectado): no es un conteo.
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
        finally:
            correr("git", "worktree", "remove", "--force", str(destino), chequear=False)


def c05(arbol: str | None) -> None:
    if arbol is None:
        anotar("C05", False, "no hay fusión que revisar (C01)")
        return
    faltas = []
    if mostrar(arbol, f"{ARCHIVO}/proposal.md") is None:
        faltas.append(f"no está {ARCHIVO}")
    if correr("git", "ls-tree", "-d", arbol, ACTIVO).stdout.strip():
        faltas.append(f"sigue el change activo {ACTIVO}")
    if mostrar(arbol, "CLAUDE.md") != mostrar(arbol, "AGENTS.md"):
        faltas.append("CLAUDE.md y AGENTS.md difieren")
    if "✅ 3f ejemplo-robusto" not in (mostrar(arbol, "CHANGES.md") or ""):
        faltas.append("CHANGES.md no marca el 3f como hecho")
    fichas = mostrar(arbol, "knowledge-base/12_fichas_de_changes.md") or ""
    if "### 3f · `ejemplo-robusto`" not in fichas or "Deuda del cierre del 3f" not in fichas:
        faltas.append("la ficha del 3f o su deuda del cierre no están")
    anotar("C05", not faltas, "; ".join(faltas) or "archivado, CHANGES y ficha al día, CLAUDE == AGENTS")


def main() -> int:
    correr("git", "fetch", "-q", "origin")
    cabeza = json.loads(correr("gh", "pr", "view", str(PR), "--repo", REPO, "--json", "headRefOid").stdout)["headRefOid"]
    fusion = correr("git", "merge-tree", "--write-tree", "--name-only", BASE, cabeza, chequear=False)
    lineas = fusion.stdout.split("\n")
    arbol = lineas[0].strip() if fusion.returncode == 0 else None
    conflictos = ", ".join(l for l in lineas[1:] if l and not l.startswith(("Auto", "CONFLICT")))
    c01(arbol, conflictos)
    c02(cabeza)
    c03(arbol, cabeza)
    c05(arbol)
    print(f"H-001 · PR #{PR} · cabeza {cabeza[:7]} sobre {BASE}")
    for criterio, ok, detalle in resultados:
        print(f"  H-001.{criterio}  {'PASA ' if ok else 'FALLA'}  {detalle}")
    print("  H-001.C06  manual  demo con Juani: evidencia en HISTORIAS.md")
    return 0 if all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
