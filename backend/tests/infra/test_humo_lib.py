"""Funciones del humo que se prueban sin Docker (`infra/ci/humo-lib.sh`, cambio 2e `humo-y-ci`).

Escenarios de `integracion-continua`: El verificador de cabeceras no acepta de más; El chequeo de
capacidades cubre todos los servicios; Cada paso del humo dice cuál es y deja su evidencia (volcado
lento).
"""

import re
import subprocess
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
PASOS = RAIZ / "infra" / "ci" / "pasos.sh"
LIB = RAIZ / "infra" / "ci" / "humo-lib.sh"
HUMO = RAIZ / "infra" / "ci" / "humo.sh"
COMPOSE = RAIZ / "infra" / "compose.yaml"

_BUENAS = (
    "HTTP/1.1 200 OK\r\n"
    "X-Content-Type-Options: nosniff\r\n"
    "Referrer-Policy: no-referrer\r\n"
    "X-Frame-Options: DENY\r\n"
    "Permissions-Policy: geolocation=(), microphone=(), camera=()\r\n"
    "Content-Type: text/html\r\n"
)


def _bash(cuerpo: str, entrada: str | None = None) -> subprocess.CompletedProcess[str]:
    script = f'set -euo pipefail\nsource "{PASOS}"\nsource "{LIB}"\n{cuerpo}\n'
    return subprocess.run(
        ["bash", "-c", script],
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def _verificar(encabezados: str) -> subprocess.CompletedProcess[str]:
    """Los encabezados entran por stdin: ninguna comilla ni barra que escapar."""
    return _bash(
        "paso 1 'cabeceras'\n"
        'encabezados="$(cat)"\n'
        'verificar_cabeceras "GET de prueba" "$encabezados"\n',
        entrada=encabezados,
    )


def test_la_lib_existe_y_esta_fuenteada_por_el_humo() -> None:
    assert LIB.exists(), "falta infra/ci/humo-lib.sh"
    assert "humo-lib.sh" in HUMO.read_text(encoding="utf-8")


def test_cabeceras_correctas_pasan() -> None:
    resultado = _verificar(_BUENAS)
    assert resultado.returncode == 0, resultado.stderr


def test_una_cabecera_de_seguridad_repetida_se_rechaza() -> None:
    resultado = _verificar(_BUENAS + "X-Frame-Options: DENY\r\n")
    assert resultado.returncode != 0
    assert "X-Frame-Options" in resultado.stderr
    assert "GET de prueba" in resultado.stderr


def test_un_valor_con_texto_de_mas_se_rechaza_nombrando_los_dos_valores() -> None:
    resultado = _verificar(
        _BUENAS.replace(
            "Referrer-Policy: no-referrer", "Referrer-Policy: no-referrer-when-downgrade"
        )
    )
    assert resultado.returncode != 0
    assert "no-referrer-when-downgrade" in resultado.stderr
    assert "no-referrer'" in resultado.stderr


def test_una_directiva_con_prefijo_ajeno_no_cuenta_como_negada() -> None:
    """`xcamera=()` no es `camera=()`: la palabra tiene que ir entera (N-a)."""
    resultado = _verificar(_BUENAS.replace(", camera=()", ", xcamera=()"))
    assert resultado.returncode != 0
    assert "camera" in resultado.stderr


def test_una_cabecera_prohibida_se_rechaza() -> None:
    resultado = _verificar(_BUENAS + "Server: Caddy\r\n")
    assert resultado.returncode != 0
    assert "Server" in resultado.stderr


def _con_dumps(cuerpo: str) -> subprocess.CompletedProcess[str]:
    return _bash(
        'carpeta="$(mktemp -d)"\n'
        "contar_dumps() {\n"
        '  find "$carpeta" -maxdepth 1 -name "proptech-*.dump" | wc -l | tr -d "[:space:]"\n'
        "}\n"
        "paso 1 'dumps'\n"
        f"{cuerpo}\n"
        'rm -rf "$carpeta"\n'
    )


def test_un_volcado_lento_se_espera_y_cuenta_uno() -> None:
    resultado = _con_dumps(
        '(sleep 2; touch "$carpeta/proptech-1.dump") &\n'
        "esperar_dumps 1 10\n"
        'echo "dumps=$(contar_dumps)"\n'
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "dumps=1" in resultado.stdout


def test_dos_volcados_donde_se_esperaba_uno_falla_nombrando_el_conteo() -> None:
    resultado = _con_dumps(
        'touch "$carpeta/proptech-1.dump" "$carpeta/proptech-2.dump"\nesperar_dumps 1 3\n'
    )
    assert resultado.returncode != 0
    assert "2" in resultado.stderr
    assert "1" in resultado.stderr


def test_ningun_volcado_dentro_del_plazo_falla() -> None:
    resultado = _con_dumps("esperar_dumps 1 1\n")
    assert resultado.returncode != 0
    assert "0" in resultado.stderr


def test_el_humo_espera_los_volcados_en_vez_de_contarlos_de_golpe() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    assert "esperar_dumps 1" in texto
    assert not re.search(r"dumps_tras_primer_arranque=\$\(contar_dumps\)", texto)


def test_un_servicio_sin_capacidades_declaradas_se_rechaza_nombrandolo() -> None:
    resultado = _bash(
        "declare -A CAPBND_ESPERADO=([api]=0000000000000000 [db]=00000000000000c3)\n"
        "paso 1 'servicios'\n"
        "verificar_servicios_declarados api db noveno\n"
    )
    assert resultado.returncode != 0
    assert "noveno" in resultado.stderr


def test_una_capacidad_declarada_de_un_servicio_que_ya_no_existe_se_rechaza() -> None:
    resultado = _bash(
        "declare -A CAPBND_ESPERADO=([api]=0000000000000000 [viejo]=0000000000000000)\n"
        "paso 1 'servicios'\n"
        "verificar_servicios_declarados api\n"
    )
    assert resultado.returncode != 0
    assert "viejo" in resultado.stderr


def test_los_servicios_declarados_en_el_humo_son_los_de_compose() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    bloque = re.search(r"declare -A CAPBND_ESPERADO=\((.*?)\n\)", texto, flags=re.DOTALL)
    assert bloque is not None, "falta el arreglo CAPBND_ESPERADO en humo.sh"
    declarados = set(re.findall(r"\[([a-z_]+)\]=", bloque.group(1)))
    en_compose = set(yaml.safe_load(COMPOSE.read_text())["services"])
    assert declarados == en_compose
    assert "config --services" in texto


def test_db_no_declara_init_true() -> None:
    """N9: con `init: true` el PID 1 de `db` es `docker-init` (root) y el chequeo de PID 1 del
    humo da rojo; hoy ningún servicio lo declara."""
    servicios = yaml.safe_load(COMPOSE.read_text())["services"]
    con_init = [nombre for nombre, datos in servicios.items() if datos.get("init")]
    assert con_init == []


_POLITICA_COMPLEJO = (
    "complejo|aislamiento_por_administracion|PERMISSIVE|{proptech_app}|ALL|"
    "(administracion_id = (current_setting('app.administracion_id'::text))::uuid)|"
    "(administracion_id = (current_setting('app.administracion_id'::text))::uuid)"
)


def _comparar(en_uso: str, restaurada: str) -> subprocess.CompletedProcess[str]:
    """Las dos listas de políticas entran por heredocs: ninguna comilla que escapar."""
    return _bash(
        "paso 1 'politicas'\n"
        f"en_uso=$(cat <<'FIN'\n{en_uso}\nFIN\n)\n"
        f"restaurada=$(cat <<'FIN'\n{restaurada}\nFIN\n)\n"
        'verificar_politicas_iguales complejo "$en_uso" "$restaurada"\n'
    )


def test_politicas_identicas_pasan() -> None:
    resultado = _comparar(_POLITICA_COMPLEJO, _POLITICA_COMPLEJO)
    assert resultado.returncode == 0, resultado.stderr


def test_una_politica_debilitada_con_la_misma_cantidad_se_rechaza_nombrandola() -> None:
    debil = _POLITICA_COMPLEJO.split("|(administracion_id")[0] + "|(true)|(true)"
    resultado = _comparar(_POLITICA_COMPLEJO, debil)
    assert resultado.returncode != 0
    assert "complejo" in resultado.stderr
    assert "aislamiento_por_administracion" in resultado.stderr


def test_una_politica_renombrada_se_rechaza_nombrando_los_dos_nombres() -> None:
    renombrada = _POLITICA_COMPLEJO.replace("aislamiento_por_administracion", "otra_politica")
    resultado = _comparar(_POLITICA_COMPLEJO, renombrada)
    assert resultado.returncode != 0
    assert "aislamiento_por_administracion" in resultado.stderr
    assert "otra_politica" in resultado.stderr


def test_una_politica_que_falta_en_la_restaurada_se_rechaza() -> None:
    resultado = _comparar(_POLITICA_COMPLEJO, "")
    assert resultado.returncode != 0
    assert "aislamiento_por_administracion" in resultado.stderr


def test_el_humo_compara_el_contenido_de_las_politicas_no_su_cantidad() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    assert "verificar_politicas_iguales" in texto
    assert "select count(*) from pg_policies" not in texto
