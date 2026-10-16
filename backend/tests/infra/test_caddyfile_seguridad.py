"""Cabeceras de seguridad y volúmenes de Caddy, parte estática (D1, D2,
tarea 3.1). La parte de punta a punta (contra el stack vivo, con el 502 de
Caddy) es de la tarea 5.3 (L-004: otro camino).

Escenarios de `entorno-de-ejecucion`: Respuesta de la web y de la API
(cabeceras); Error del proxy (las mismas cabeceras en un 502 de Caddy);
Caddy recreado conserva sus datos (los volúmenes, parte estática).
"""

import json
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


def test_el_caddyfile_fija_las_cuatro_cabeceras_de_seguridad() -> None:
    texto = CADDYFILE.read_text()
    for cabecera in _CABECERAS_DE_SEGURIDAD:
        assert cabecera in texto, f"falta la cabecera {cabecera} en el Caddyfile"


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
    del sitio, no duplicadas (ni olvidadas) dentro de cada `handle`."""
    texto = CADDYFILE.read_text()
    assert texto.count("X-Content-Type-Options") <= 2  # el header normal + handle_errors


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
