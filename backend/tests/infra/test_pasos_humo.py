"""Tests de efecto (sin Docker) sobre `infra/ci/pasos.sh` (D6, tarea 2.1).

`pasos.sh` da a `humo.sh` un único mecanismo para que un paso que falla
nombre su número, su descripción, la línea y el comando: un único
`trap ... ERR` con `set -E`, que cubre los 35 `[ ]` y los 11 `grep -q`
sueltos de humo.sh sin reescribir cada uno a `if !` (L-014: los `if !` que
ya existen, con su propio manejo de error, se quedan como están).

Estos tests corren el mecanismo en un script mínimo, nunca contra Docker
(L-018: se verifica el efecto del helper, no su forma).
"""

import re
import subprocess
import textwrap
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PASOS = RAIZ / "infra" / "ci" / "pasos.sh"
HUMO = RAIZ / "infra" / "ci" / "humo.sh"


def _correr_script(cuerpo: str) -> subprocess.CompletedProcess[str]:
    """Ejecuta `cuerpo` en un script temporal que primero `source`ea
    `pasos.sh` (con su ruta absoluta, para no depender del directorio
    desde el que corre pytest)."""
    script = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source "{PASOS}"
        {cuerpo}
        """)
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )


def test_pasos_sh_existe() -> None:
    assert PASOS.exists(), "falta infra/ci/pasos.sh"


def test_un_corchete_suelto_que_falla_nombra_numero_descripcion_linea_y_comando() -> None:
    resultado = _correr_script('paso 1 "corchete de prueba"\n[ 1 = 2 ]\n')
    assert resultado.returncode != 0
    assert "1" in resultado.stderr
    assert "corchete de prueba" in resultado.stderr
    assert re.search(r"l[íi]nea\s+\d+", resultado.stderr), resultado.stderr
    assert "[ 1 = 2 ]" in resultado.stderr


def test_un_grep_q_suelto_que_falla_nombra_numero_descripcion_linea_y_comando() -> None:
    resultado = _correr_script(
        'paso 2 "grep de prueba"\necho "contenido" | grep -q "no-esta-aca"\n'
    )
    assert resultado.returncode != 0
    assert "2" in resultado.stderr
    assert "grep de prueba" in resultado.stderr
    assert re.search(r"l[íi]nea\s+\d+", resultado.stderr), resultado.stderr
    assert "grep -q" in resultado.stderr


def test_un_if_negado_reportado_a_mano_nombra_numero_descripcion_linea_y_comando() -> None:
    """L-014: el trap no salta dentro de un `if`; `reportar_fallo_paso` es el
    mismo formateador, invocable a mano desde ese caso (no se usa hoy en
    humo.sh: sus `if !` existentes se quedan como están)."""
    resultado = _correr_script(
        'paso 3 "if negado de prueba"\n'
        "if ! grep -q no-esta-aca <<< contenido; then\n"
        '  reportar_fallo_paso "$LINENO" "grep -q no-esta-aca"\n'
        "  exit 1\n"
        "fi\n"
    )
    assert resultado.returncode != 0
    assert "3" in resultado.stderr
    assert "if negado de prueba" in resultado.stderr
    assert re.search(r"l[íi]nea\s+\d+", resultado.stderr), resultado.stderr
    assert "grep -q no-esta-aca" in resultado.stderr


def test_humo_usa_pasos_sh_en_sus_27_pasos() -> None:
    """humo.sh tiene que fuentear pasos.sh y anunciar sus 27 pasos con
    `paso N "descripción"`, no con `echo "--- (N) descripción ---"` suelto
    (que no deja nada para que el trap reporte al fallar)."""
    texto = HUMO.read_text(encoding="utf-8")
    assert "pasos.sh" in texto, "humo.sh no fuentea infra/ci/pasos.sh"
    llamadas_a_paso = re.findall(r'^\s*paso\s+\S+\s+"', texto, flags=re.MULTILINE)
    assert len(llamadas_a_paso) == 27, (
        f"se esperaban 27 llamadas a `paso N ...` en humo.sh, se encontraron {len(llamadas_a_paso)}"
    )
    assert not re.search(r'^echo "--- \(', texto, flags=re.MULTILINE), (
        "quedó un encabezado de paso anunciado con echo suelto en vez de `paso`"
    )


def test_un_exit_explicito_reportado_con_fallar_paso_nombra_paso_linea_y_condicion() -> None:
    """2e, C2-5: un `exit 1` explícito (el que `trap ERR` no ve, L-014) pasa por
    `fallar_paso`, que usa el mismo formateador y termina distinto de 0."""
    resultado = _correr_script(
        'paso 4 "exit explícito de prueba"\n'
        'if [ 1 = 2 ]; then echo "no pasa"; else\n'
        '  echo "ERROR: algo salió mal" >&2\n'
        "  fallar_paso '[ 1 = 2 ]'\n"
        "fi\n"
    )
    assert resultado.returncode == 1
    assert "algo salió mal" in resultado.stderr
    assert "paso 4 (exit explícito de prueba)" in resultado.stderr
    assert re.search(r"l[íi]nea\s+\d+", resultado.stderr), resultado.stderr
    assert "[ 1 = 2 ]" in resultado.stderr


def test_una_falla_dentro_de_una_funcion_nombra_la_linea_del_llamado() -> None:
    """2e, C2V2-8: `compose()` (y cualquier helper) falla en su propia línea; el informe tiene
    que decir también desde qué línea del script se lo llamó."""
    cuerpo = (
        'paso 5 "falla en una función"\nfalla_adentro() {\n  false\n}\nfalla_adentro # LLAMADO\n'
    )
    resultado = _correr_script(cuerpo)
    assert resultado.returncode != 0
    script = f'#!/usr/bin/env bash\nset -euo pipefail\nsource "{PASOS}"\n{cuerpo}'
    linea_del_llamado = next(
        numero for numero, linea in enumerate(script.splitlines(), 1) if "# LLAMADO" in linea
    )
    assert f"llamado desde la línea {linea_del_llamado}" in resultado.stderr, resultado.stderr


def test_una_falla_fuera_de_funciones_no_inventa_un_llamado() -> None:
    resultado = _correr_script('paso 6 "falla suelta"\nfalse\n')
    assert resultado.returncode != 0
    assert "llamado desde" not in resultado.stderr


def test_humo_no_tiene_ningun_exit_1_pelado() -> None:
    """2e, C2-5 y C2V2-8: todo camino de falla del humo pasa por `fallar_paso` (o por el
    rechazo previo, que corre antes de cualquier paso). Un `exit 1` pelado deja una falla
    sin línea ni comando."""
    texto = HUMO.read_text(encoding="utf-8")
    sin_rechazo = re.sub(r"rechazar\(\) \{.*?\n\}\n", "", texto, flags=re.DOTALL)
    sueltos = [
        linea.strip()
        for linea in sin_rechazo.splitlines()
        if re.search(r"\bexit 1\b", linea) and not linea.strip().startswith("#")
    ]
    assert not sueltos, f"'exit 1' sin pasar por fallar_paso: {sueltos}"
    assert "fallar_paso" in texto
