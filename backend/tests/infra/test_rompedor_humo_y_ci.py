"""Rompedor del cambio 2e `humo-y-ci`: huecos que los tests del constructor no ven.

Cada test fija un hallazgo (ver el informe del rompedor). Sin Docker: `docker` falso en el PATH,
scripts mínimos que fuentean `pasos.sh`/`humo-lib.sh`, y lectura estática de `Caddyfile`/`humo.sh`.
"""

import os
import re
import shutil
import socket
import subprocess
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
CI = RAIZ / "infra" / "ci"
PASOS = CI / "pasos.sh"
LIB = CI / "humo-lib.sh"
HUMO = CI / "humo.sh"
ENSAYO = CI / "ensayo-roles.sh"
CADDYFILE = RAIZ / "infra" / "Caddyfile"

#: `docker` falso: registra cada invocación. `ps -q` (sólo corriendo) no devuelve nada; `ps -aq`
#: (también detenidos) y `volume ls -q` devuelven lo del stack real DETENIDO. Todo `up` falla, así
#: el script baja enseguida por su `trap` (y se ve si ese `trap` hace `down -v`).
_DOCKER_FALSO = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
if [ "$1" = "ps" ]; then
  case " $* " in
    *" -a"*|*" --all "*) printf '%s\\n' "${STUB_PS_AQ:-}" ;;
    *) printf '%s' "${STUB_PS_Q:-}" ;;
  esac
  exit 0
fi
if [ "$1" = "volume" ]; then
  printf '%s\\n' "${STUB_VOLUMENES:-}"
  exit 0
fi
if [ "$1" = "compose" ]; then
  case " $* " in
    *" up "*) exit 1 ;;
  esac
fi
exit 0
"""


def _puerto_libre() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return int(sonda.getsockname()[1])


def _montar(tmp_path: Path) -> Path:
    ci = tmp_path / "infra" / "ci"
    ci.mkdir(parents=True)
    for nombre in ("humo.sh", "pasos.sh", "humo-lib.sh", "ensayo-roles.sh"):
        shutil.copy(CI / nombre, ci / nombre)
    (tmp_path / "backend").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / ".git").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(_DOCKER_FALSO)
    docker.chmod(0o755)
    return ci


def _correr(
    tmp_path: Path, script: str, entorno_extra: dict[str, str]
) -> tuple[int, str, list[str]]:
    ci = _montar(tmp_path)
    registro = tmp_path / "docker.log"
    registro.write_text("")
    entorno = {
        "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "STUB_LOG": str(registro),
        "PROPTECH_HUMO_PUERTOS": str(_puerto_libre()),
        **entorno_extra,
    }
    resultado = subprocess.run(
        ["bash", str(ci / script)],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    llamadas = [linea for linea in registro.read_text().splitlines() if linea.startswith("compose")]
    return resultado.returncode, resultado.stderr, llamadas


# --- R1 (ALTA): el stack real DETENIDO no está protegido -------------------------------------


# --- R2 (ALTA): ensayo-roles.sh, ahora en el CI, sigue con `proptech` por defecto ---------------


# --- R3 (MEDIA): dos pasos con el mismo número --------------------------------------------------


def test_cada_paso_del_humo_tiene_un_numero_propio() -> None:
    """La spec pide que la falla nombre "su número": con dos `paso 6c`, un rojo en 6c no dice
    cuál de los dos pasos fue."""
    numeros = re.findall(r"^paso (\S+) ", HUMO.read_text(encoding="utf-8"), flags=re.MULTILINE)
    repetidos = [numero for numero, veces in Counter(numeros).items() if veces > 1]
    assert repetidos == [], f"números de paso repetidos en humo.sh: {repetidos}"


# --- R4 (MEDIA): `fallar_paso` dentro de un helper nombra la línea del helper -------------------


def test_una_falla_dentro_de_un_helper_nombra_la_linea_del_llamado() -> None:
    """Escenario "Falla dentro de compose" generalizado: `verificar_cabeceras` se llama 11 veces
    desde humo.sh; `fallar_paso` informa `BASH_LINENO[0]`, que es la línea DENTRO de humo-lib.sh,
    sin archivo y sin "llamado desde": el número apunta a una línea cualquiera de humo.sh."""
    script = (
        "set -euo pipefail\n"  # línea 1
        f'source "{PASOS}"\n'  # línea 2
        f'source "{LIB}"\n'  # línea 3
        "paso 1 'helper'\n"  # línea 4
        'verificar_cabeceras "GET de prueba" "HTTP/1.1 200 OK"\n'  # línea 5: el llamado
    )
    resultado = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=30, check=False
    )
    assert resultado.returncode != 0
    assert re.search(r"(llamado desde la )?l[íi]nea 5\b", resultado.stderr), resultado.stderr


# --- R5 (MEDIA): el bucle de los ocho métodos no mira las cabeceras ----------------------------


def test_el_bucle_de_los_ocho_metodos_verifica_las_cabeceras_de_cada_respuesta() -> None:
    """Escenario "Ocho métodos": "las ocho respuestas son 421, vacías y CON las cabeceras de
    seguridad". El bucle hace `-o /dev/null -w '%{http_code} %{size_download}'`: un `header` del
    sitio de respaldo restringido a GET pasa el humo entero (mutante M5 del informe)."""
    texto = HUMO.read_text(encoding="utf-8")
    inicio = texto.index("for metodo in GET HEAD")
    cuerpo = texto[inicio : texto.index("\ndone\n", inicio)]
    assert "verificar_cabeceras" in cuerpo, "el bucle de los ocho métodos no verifica cabeceras"


# --- R6 (BAJA): el test de timeouts mira sólo el primer reverse_proxy de cada destino ----------


def _sin_comentarios(texto: str) -> str:
    return "\n".join(linea for linea in texto.splitlines() if not linea.strip().startswith("#"))


def _bloques_de_reverse_proxy(texto: str) -> list[str]:
    bloques = []
    for coincidencia in re.finditer(r"reverse_proxy\s+\S+", texto):
        inicio = coincidencia.start()
        fin_de_linea = texto.index("\n", inicio)
        if not texto[inicio:fin_de_linea].rstrip().endswith("{"):
            bloques.append(texto[inicio:fin_de_linea])
            continue
        profundidad = 0
        for posicion in range(inicio, len(texto)):
            if texto[posicion] == "{":
                profundidad += 1
            elif texto[posicion] == "}":
                profundidad -= 1
                if profundidad == 0:
                    bloques.append(texto[inicio : posicion + 1])
                    break
    return bloques


def test_todos_los_reverse_proxy_tienen_timeouts_no_solo_el_primero() -> None:
    texto = _sin_comentarios(CADDYFILE.read_text(encoding="utf-8"))
    bloques = _bloques_de_reverse_proxy(texto)
    assert bloques
    for bloque in bloques:
        cabecera = bloque.splitlines()[0]
        assert re.search(r"dial_timeout\s+\S+", bloque), f"sin dial_timeout: {cabecera}"
        assert re.search(r"response_header_timeout\s+\S+", bloque), (
            f"sin response_header_timeout: {cabecera}"
        )


# --- R7 (BAJA): la declaración del 443 no ve un sitio `https://` --------------------------------


def test_la_declaracion_del_443_ve_cualquier_sitio_https() -> None:
    """`^\\s*:?443\\b` sólo ve `:443 {` o `443 {`; un `https:// {`, `*:443 {` o
    `localhost:443 {` cambian la conducta del 443 sin que el test de la declaración se entere."""
    texto = _sin_comentarios(CADDYFILE.read_text(encoding="utf-8"))
    direcciones = [
        linea for linea in texto.splitlines() if linea and not linea[0].isspace() and "{" in linea
    ]
    https = [d for d in direcciones if re.search(r"https://|:443\b|^443\b", d)]
    assert https == [], f"sitio para el 443 sin actualizar la declaración: {https}"


# --- R11 (BAJA): guardas sin test (mutantes M1 y M2 sobrevivían) -------------------------------


def test_el_rechazo_por_puertos_mira_el_80_y_el_443_por_defecto() -> None:
    """Mutante M1: `PROPTECH_HUMO_PUERTOS:-80 443` -> `:-80` dejaba los 39 tests del humo en verde
    (todos fijan la variable). El 443 lo publica Caddy fijo igual que el 80."""
    texto = HUMO.read_text(encoding="utf-8")
    por_defecto = re.search(r"\$\{PROPTECH_HUMO_PUERTOS:-([0-9 ]+)\}", texto)
    assert por_defecto is not None
    assert set(por_defecto.group(1).split()) == {"80", "443"}


_POLITICA = (
    "complejo|complejo_por_administracion|PERMISSIVE|{proptech_app}|ALL|"
    "(administracion_id = x)|(administracion_id = x)"
)


def test_una_politica_que_sobra_en_la_restaurada_se_rechaza_nombrandola() -> None:
    """Mutante M2: sin el segundo bucle de `verificar_politicas_iguales`, una política PERMISIVA
    extra en la base restaurada (que con OR abre la tabla) pasaba los 19 tests de humo-lib."""
    extra = "complejo|abre_todo|PERMISSIVE|{public}|ALL|true|true"
    script = (
        f'set -euo pipefail\nsource "{PASOS}"\nsource "{LIB}"\n'
        "paso 11 'politicas'\n"
        f"en_uso=$(cat <<'FIN'\n{_POLITICA}\nFIN\n)\n"
        f"restaurada=$(cat <<'FIN'\n{_POLITICA}\n{extra}\nFIN\n)\n"
        'verificar_politicas_iguales complejo "$en_uso" "$restaurada"\n'
    )
    resultado = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=30, check=False
    )
    assert resultado.returncode != 0
    assert "abre_todo" in resultado.stderr
