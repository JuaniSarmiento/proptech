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


def test_humo_usa_pasos_sh_en_sus_25_pasos() -> None:
    """humo.sh tiene que fuentear pasos.sh y anunciar sus 25 pasos con
    `paso N "descripción"`, no con `echo "--- (N) descripción ---"` suelto
    (que no deja nada para que el trap reporte al fallar)."""
    texto = HUMO.read_text()
    assert "pasos.sh" in texto, "humo.sh no fuentea infra/ci/pasos.sh"
    llamadas_a_paso = re.findall(r'^\s*paso\s+\S+\s+"', texto, flags=re.MULTILINE)
    assert len(llamadas_a_paso) == 25, (
        f"se esperaban 25 llamadas a `paso N ...` en humo.sh, se encontraron {len(llamadas_a_paso)}"
    )
    assert not re.search(r'^echo "--- \(', texto, flags=re.MULTILINE), (
        "quedó un encabezado de paso anunciado con echo suelto en vez de `paso`"
    )
