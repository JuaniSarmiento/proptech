"""Aceptación de H-002: integrar el PR #5 `humo-y-ci` (C-23, 2e) a `main`.

Se corre desde la raíz del repo, con `gh` autenticado y Docker andando:

    python3 aceptacion/H-002/aceptar.py

Verifica sobre la fusión de `origin/main` con la cabeza del PR, sin tocar el árbol de trabajo:
  C01  la fusión no tiene conflictos; ninguna D ni L se repite; la decisión del 2e es D-147 y sus
       tres lecciones dejaron L-068 a L-070 (que en `main` son de otro change); las líneas que agrega
       el PR no nombran D-144 ni L-068 a L-070.
  C02  la cabeza del PR tiene todos sus checks en verde y un run del evento pull_request.
  C03  los 19 archivos de tests que prueban el change corren completos sobre la fusión: 167
       esperados, 167 pasados, ningún skip, falla ni error. Quedan afuera los tres a los que el PR
       sólo les tocó la preparación (test_rutas_protegidas, test_salud_cola_real y
       test_zz_rompedor_api_application_name): los corre la suite completa del CI (C02).
  C05  el change está archivado con sus specs sincronizadas, CHANGES.md y la ficha lo dan por cerrado,
       CLAUDE.md == AGENTS.md.
  C06  ninguna tarea del change quedó sin marcar (incluida la 10.4).
  C07  humo.sh y ensayo-roles.sh terminan con 1 sin llamar a docker cuando falta
       PROPTECH_COMPOSE_PROYECTO, cuando vale `proptech` y cuando un puerto que miran está ocupado;
       con otro nombre y los puertos libres, pasan la guarda y llegan a docker. Se corren con un
       `docker` falso en el PATH: ningún caso toca un stack real.
C08 (demo) no es ejecutable: se registra como evidencia en HISTORIAS.md.

Sale con 0 sólo si todos los criterios pasan.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

PR = 5
BASE = "origin/main"
REPO = "JuaniSarmiento/proptech"
CAMBIO = "humo-y-ci"
DECISION = 147
LECCIONES_DEL_PR = (
    "La evidencia verde de un job de CI se saca de una copia limpia",
    "Paralelizar muestra las dependencias de orden y de arranque",
    "Rechazar un nombre es más fuerte que rechazar un estado",
)
NUMEROS_VIEJOS = re.compile(r"D-144\b|L-06[89]\b|L-070\b")
TESTS = [
    "tests/infra/test_backend_paralelo.py",
    "tests/infra/test_caddy_respaldo_y_timeouts.py",
    "tests/infra/test_ci_workflow.py",
    "tests/infra/test_coleccion_determinista.py",
    "tests/infra/test_dependabot.py",
    "tests/infra/test_ensayo_login.py",
    "tests/infra/test_humo.py",
    "tests/infra/test_humo_aislamiento.py",
    "tests/infra/test_humo_lib.py",
    "tests/infra/test_openspec_fijado.py",
    "tests/infra/test_pasos_humo.py",
    "tests/infra/test_rechazos_de_scripts_destructivos.py",
    "tests/infra/test_respaldos.py",
    "tests/infra/test_rompedor_humo_y_ci.py",
    "tests/unitarios/test_arranque_fallido_completo.py",
    "tests/unitarios/test_postgres_espera_conexiones.py",
    "tests/unitarios/test_registros_del_log.py",
    "tests/unitarios/test_rompedor_log_y_arranque.py",
    "tests/unitarios/test_worker_tenant.py",
]
TESTS_ESPERADOS = 167
CHECKS_MINIMOS = 5
SCRIPTS = ("infra/ci/humo.sh", "infra/ci/ensayo-roles.sh")

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
    decisiones = mostrar(arbol, "knowledge-base/09_decisiones_y_supuestos.md") or ""
    lecciones = mostrar(arbol, "knowledge-base/15_lecciones.md") or ""
    for nombre, texto, patron in (("D", decisiones, r"^## D-(\d+) "), ("L", lecciones, r"^## L-(\d+) ")):
        numeros = [int(n) for n in re.findall(patron, texto, flags=re.M)]
        repetidas = sorted(n for n, c in Counter(numeros).items() if c > 1)
        if repetidas:
            faltas.append(f"{nombre} repetidas: {repetidas}")
    if not re.search(rf"^## D-{DECISION} · El 2e `humo-y-ci`", decisiones, flags=re.M):
        faltas.append(f"la decisión del 2e no es D-{DECISION}")
    for titulo in LECCIONES_DEL_PR:
        m = re.search(rf"^## L-(\d+) · {re.escape(titulo)}", lecciones, flags=re.M)
        if m is None:
            faltas.append(f"falta la lección «{titulo[:30]}…»")
        elif int(m.group(1)) in (68, 69, 70):
            faltas.append(f"la lección «{titulo[:30]}…» sigue como L-{m.group(1)}")
    agregadas = [l for l in correr("git", "diff", BASE, arbol).stdout.splitlines()
                 if l.startswith("+") and not l.startswith("+++") and NUMEROS_VIEJOS.search(l)]
    if agregadas:
        faltas.append(f"{len(agregadas)} líneas agregadas nombran D-144 o L-068 a L-070, la primera: {agregadas[0][:100]}")
    anotar("C01", not faltas, "; ".join(faltas) or f"sin conflictos; D-{DECISION}, lecciones renumeradas, ninguna D ni L repetida")


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
    with tempfile.TemporaryDirectory(prefix="aceptacion-h002-junit-") as tmp:
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
    if mostrar(arbol, "CLAUDE.md") != mostrar(arbol, "AGENTS.md"):
        faltas.append("CLAUDE.md y AGENTS.md difieren")
    if "✅ 2e humo-y-ci" not in (mostrar(arbol, "CHANGES.md") or ""):
        faltas.append("CHANGES.md no marca el 2e como hecho")
    if "### 2e · `humo-y-ci`" not in (mostrar(arbol, "knowledge-base/12_fichas_de_changes.md") or ""):
        faltas.append("no está la ficha del 2e")
    anotar("C05", not faltas, "; ".join(faltas[:4]) or "archivado, specs sincronizadas, CHANGES y ficha al día, CLAUDE == AGENTS")
    tareas = mostrar(arbol, f"{archivo}/tasks.md") if archivo else None
    if tareas is None:
        anotar("C06", False, "no hay tasks.md del change archivado")
    else:
        abiertas = re.findall(r"^\s*- \[ \] (\S+)", tareas, flags=re.M)
        hechas = len(re.findall(r"^\s*- \[x\]", tareas, flags=re.M))
        anotar("C06", not abiertas, f"tareas abiertas: {abiertas}" if abiertas else f"{hechas} tareas, todas marcadas")


def c07(destino: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="aceptacion-h002-docker-") as tmp:
        bin_falso, registro = Path(tmp) / "bin", Path(tmp) / "docker.log"
        bin_falso.mkdir()
        falso = bin_falso / "docker"
        falso.write_text(f'#!/bin/sh\necho "$*" >> "{registro}"\nexit 99\n')
        falso.chmod(0o755)
        ocupado = socket.socket()
        ocupado.bind(("127.0.0.1", 0))
        ocupado.listen()
        libre = socket.socket()
        libre.bind(("127.0.0.1", 0))
        puerto_libre = libre.getsockname()[1]
        libre.close()
        base_env = {k: v for k, v in os.environ.items() if not k.startswith("PROPTECH_")}
        base_env["PATH"] = f"{bin_falso}:{base_env['PATH']}"
        casos = (
            ("sin variable", {}, "falta PROPTECH_COMPOSE_PROYECTO", False),
            ("proptech", {"PROPTECH_COMPOSE_PROYECTO": "proptech"}, "'proptech'", False),
            ("puerto ocupado", {"PROPTECH_COMPOSE_PROYECTO": "proptech-aceptacion",
                                "PROPTECH_HUMO_PUERTOS": str(ocupado.getsockname()[1])}, "ocupado", False),
            ("otro nombre", {"PROPTECH_COMPOSE_PROYECTO": "proptech-aceptacion",
                             "PROPTECH_HUMO_PUERTOS": str(puerto_libre)}, None, True),
        )
        faltas, vistos = [], 0
        try:
            for script in SCRIPTS:
                for nombre, extra, mensaje, debe_llegar in casos:
                    registro.unlink(missing_ok=True)
                    try:
                        r = subprocess.run(["bash", script], cwd=destino, env={**base_env, **extra}, capture_output=True,
                                           text=True, timeout=120, stdin=subprocess.DEVNULL)
                        codigo, salida = r.returncode, r.stdout + r.stderr
                    except subprocess.TimeoutExpired:
                        codigo, salida = None, "timeout"
                    llamo = registro.exists() and registro.read_text().strip() != ""
                    if debe_llegar:
                        ok = llamo
                    else:
                        ok = codigo == 1 and not llamo and mensaje is not None and mensaje in salida
                    vistos += 1
                    if not ok:
                        faltas.append(f"{script} {nombre}: código {codigo}, docker {'llamado' if llamo else 'no llamado'}")
        finally:
            ocupado.close()
    anotar("C07", not faltas, "; ".join(faltas) or f"{vistos} casos: tres rechazos sin docker y el nombre propio llega a docker, en los dos scripts")


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
        anotar("C07", False, "no hay fusión sobre la que correr los scripts (C01)")
    else:
        base = correr("git", "rev-parse", BASE).stdout.strip()
        commit = correr("git", "commit-tree", arbol, "-p", base, "-p", cabeza, "-m", "aceptacion H-002").stdout.strip()
        # Un clon y no un worktree: ensayo-roles.sh escribe su evidencia en `.git/`, que en un worktree
        # es un archivo.
        with tempfile.TemporaryDirectory(prefix="aceptacion-h002-") as tmp:
            destino = Path(tmp) / "arbol"
            correr("git", "clone", "-q", "--shared", "--no-checkout", str(Path.cwd()), str(destino))
            correr("git", "-C", str(destino), "checkout", "-q", "--detach", commit)
            c07(destino)
            c03(destino)
    print(f"H-002 · PR #{PR} · cabeza {cabeza[:7]} sobre {BASE}")
    for criterio, ok, detalle in sorted(resultados):
        print(f"  H-002.{criterio}  {'PASA ' if ok else 'FALLA'}  {detalle}")
    print("  H-002.C08  manual  demo con Juani: evidencia en HISTORIAS.md")
    return 0 if all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
