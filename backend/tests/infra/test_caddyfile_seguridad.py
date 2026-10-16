"""Cabeceras de seguridad y volúmenes de Caddy, parte estática (D1, D2,
tarea 3.1). La parte de punta a punta (contra el stack vivo, con el 502 de
Caddy) es de la tarea 5.3 (L-004: otro camino).

Escenarios de `entorno-de-ejecucion`: Respuesta de la web y de la API
(cabeceras); Error del proxy (las mismas cabeceras en un 502 de Caddy);
Caddy recreado conserva sus datos (los volúmenes, parte estática).

C2-1 (rompedor/auditor, vuelta 1 del 2c): hasta acá, los tests sólo miraban
que la cabecera EXISTIERA; un `Referrer-Policy: unsafe-url` o un
`X-Frame-Options: ALLOWALL` pasaban todo (M11/M12, L-019). Ahora se exige
el VALOR de las cuatro.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
CADDYFILE = RAIZ / "infra" / "Caddyfile"
COMPOSE = RAIZ / "infra" / "compose.yaml"
NEXT_CONFIG = RAIZ / "web" / "next.config.ts"

SITIO_DE_PRUEBA = "example.invalid"

_CABECERAS_DE_SEGURIDAD = (
    "X-Content-Type-Options",
    "Referrer-Policy",
    "X-Frame-Options",
    "Permissions-Policy",
)
_CABECERAS_A_QUITAR = ("Server", "Via", "X-Powered-By")

#: Juani confirmó `Referrer-Policy: no-referrer` (como dice la spec y D1),
#: no `strict-origin-when-cross-origin` (C2-1, vuelta 2 del 2c).
_VALOR_ESPERADO = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
#: Permissions-Policy: cada directiva, vacía (niega el permiso), sin
#: importar el orden entre las tres (L-021: no atarse a la grafía literal
#: de hoy).
_DIRECTIVAS_PERMISSIONS_POLICY = ("camera", "microphone", "geolocation")


def _valores_de_cabeceras(texto: str) -> dict[str, list[str]]:
    """Cada ocurrencia de `Cabecera valor` en un bloque `header { ... }` del
    Caddyfile (una lista: la cabecera puede repetirse en más de un bloque,
    p.ej. el sitio y `handle_errors`)."""
    valores: dict[str, list[str]] = {c: [] for c in _CABECERAS_DE_SEGURIDAD}
    for cabecera in _CABECERAS_DE_SEGURIDAD:
        patron = re.compile(rf'^\s*{re.escape(cabecera)}\s+"?([^"\n]+?)"?\s*$', re.MULTILINE)
        valores[cabecera] = [m.strip() for m in patron.findall(texto)]
    return valores


def _compose() -> dict[str, Any]:
    datos = yaml.safe_load(COMPOSE.read_text())
    assert isinstance(datos, dict)
    return datos


def _imagen_caddy() -> str:
    return str(_compose()["services"]["caddy"]["image"])


def _caddy_adapt_validate() -> dict[str, Any]:
    resultado = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            f"PROPTECH_SITIO={SITIO_DE_PRUEBA}",
            "-v",
            f"{CADDYFILE}:/etc/caddy/Caddyfile:ro",
            _imagen_caddy(),
            "caddy",
            "adapt",
            "--validate",
            "--config",
            "/etc/caddy/Caddyfile",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert resultado.returncode == 0, (
        f"caddy adapt --validate falló: {resultado.stderr}\n{resultado.stdout}"
    )
    primera_linea = resultado.stdout.splitlines()[0]
    return dict(json.loads(primera_linea))


def test_caddy_adapt_validate_sigue_aceptando_el_caddyfile() -> None:
    adaptado = _caddy_adapt_validate()
    assert adaptado.get("apps", {}).get("http") is not None


def test_el_caddyfile_fija_las_cuatro_cabeceras_de_seguridad_con_su_valor() -> None:
    """C2-1: no alcanza con que la cabecera exista — tiene que tener el
    valor que pide la spec. Se exige en TODOS los bloques `header` que la
    traen (el del sitio y el de `handle_errors`), no sólo en el primero."""
    texto = CADDYFILE.read_text()
    valores = _valores_de_cabeceras(texto)
    for cabecera, esperado in _VALOR_ESPERADO.items():
        encontrados = valores[cabecera]
        assert encontrados, f"falta la cabecera {cabecera} en el Caddyfile"
        for valor in encontrados:
            assert valor == esperado, (
                f"{cabecera} tiene el valor {valor!r}, se esperaba {esperado!r}"
            )

    for valor in valores["Permissions-Policy"]:
        for directiva in _DIRECTIVAS_PERMISSIONS_POLICY:
            assert re.search(rf"\b{directiva}=\(\)", valor), (
                f"Permissions-Policy ({valor!r}) no niega {directiva}"
            )


def test_el_caddyfile_quita_server_via_y_x_powered_by() -> None:
    texto = CADDYFILE.read_text()
    for cabecera in _CABECERAS_A_QUITAR:
        assert f"-{cabecera}" in texto, f"falta quitar {cabecera} en el Caddyfile"


def test_el_caddyfile_tiene_un_handle_errors_que_repite_las_mismas_cabeceras() -> None:
    """D1: `header -Server` NO alcanza a un 502 que genera el propio Caddy
    (evidencia de la revisión de DevOps, 2026-10-16 09:50): hace falta un
    `handle_errors` separado que repita el mismo tratamiento de cabeceras
    para la respuesta de error."""
    texto = CADDYFILE.read_text()
    assert "handle_errors" in texto, "falta un bloque handle_errors en el Caddyfile"
    inicio = texto.index("handle_errors")
    bloque_errores = texto[inicio:]
    for cabecera in _CABECERAS_A_QUITAR:
        assert f"-{cabecera}" in bloque_errores, f"el bloque handle_errors no quita {cabecera}"
    for cabecera in _CABECERAS_DE_SEGURIDAD:
        assert cabecera in bloque_errores, f"el bloque handle_errors no fija {cabecera}"


def test_las_cabeceras_estan_fuera_de_los_handle_de_ruta() -> None:
    """Tienen que aplicar a /api/* y a la web por igual (y a HEAD, que Go
    responde solo sin cuerpo): puestas dentro de un único `header` al nivel
    del sitio, no duplicadas (ni olvidadas) dentro de cada `handle`.
    Tres bloques `header` en todo el Caddyfile: el sitio, su
    `handle_errors` y el sitio de respaldo de C2-2 — nunca más (eso
    delataría una copia pegada dentro de un `handle`)."""
    texto = CADDYFILE.read_text()
    assert texto.count("X-Content-Type-Options") == 3


def test_el_caddyfile_tiene_un_sitio_de_respaldo_para_lo_que_no_matchea() -> None:
    """C2-2: cualquier pedido que no matchee el host de `{$PROPTECH_SITIO}`
    (por IP, Host ajeno, sin Host) caía en la respuesta por defecto de
    Caddy, fuera del `header`/`handle_errors` del sitio real — con
    `Server: Caddy` y sin ninguna cabecera. El rojo de punta a punta
    (stack vivo) es de la 6c del humo; acá sólo la forma."""
    texto = CADDYFILE.read_text()
    assert re.search(r"^:80\s*\{", texto, re.MULTILINE), (
        "falta un sitio de respaldo (':80 { ... }') para lo que no matchea el sitio real"
    )
    inicio = texto.index(":80 {")
    bloque = texto[inicio:]
    for cabecera in _CABECERAS_A_QUITAR:
        assert f"-{cabecera}" in bloque, f"el sitio de respaldo no quita {cabecera}"
    for cabecera, esperado in _VALOR_ESPERADO.items():
        assert f"{cabecera} {esperado}" in bloque, (
            f"el sitio de respaldo no fija {cabecera}: {esperado}"
        )


def test_next_config_desactiva_powered_by_header() -> None:
    texto = NEXT_CONFIG.read_text()
    assert "poweredByHeader: false" in texto, (
        "next.config.ts no tiene poweredByHeader: false (X-Powered-By seguiría viniendo de Next)"
    )


def test_compose_monta_los_dos_volumenes_de_caddy() -> None:
    """D2: `/data` y `/config` con nombre, para que `instance.uuid`
    sobreviva a un `--force-recreate` (verificado de punta a punta en la
    5.3; acá sólo la forma de compose.yaml)."""
    datos = _compose()
    caddy = datos["services"]["caddy"]
    volumenes = caddy.get("volumes") or []
    destinos = set()
    for v in volumenes:
        if isinstance(v, str) and ":" in v:
            partes = v.split(":")
            destinos.add(partes[1])
    assert "/data" in destinos, "caddy no monta un volumen en /data"
    assert "/config" in destinos, "caddy no monta un volumen en /config"

    volumenes_top = datos.get("volumes") or {}
    for v in volumenes:
        if isinstance(v, str) and v.split(":")[1:2] == ["/data"]:
            nombre = v.split(":")[0]
            assert nombre in volumenes_top, f"{nombre} no está declarado en volumes: de compose"
        if isinstance(v, str) and v.split(":")[1:2] == ["/config"]:
            nombre = v.split(":")[0]
            assert nombre in volumenes_top, f"{nombre} no está declarado en volumes: de compose"
