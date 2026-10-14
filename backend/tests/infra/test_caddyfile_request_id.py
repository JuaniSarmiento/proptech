"""Tests del `Caddyfile` y de Compose para el `request_id` a través del proxy
(D7, D8). Cambio 1c, tarea 6.4.

Escenarios de `trazabilidad-y-logs`: Cliente que manda su propio número
(configuración del proxy; la verificación de punta a punta es del humo del
1d); De la web a la API (configuración); Error del proxy con un dato en la
query (configuración).
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
CADDYFILE = RAIZ / "infra" / "Caddyfile"
COMPOSE = RAIZ / "infra" / "compose.yaml"

#: Valor de prueba para {$PROPTECH_SITIO}: sin él, un server block vacío
#: queda en una posición que no es la primera y `caddy adapt` lo rechaza
#: ("server block without any key ... must be first").
SITIO_DE_PRUEBA = "example.invalid"


def _compose() -> dict[str, Any]:
    datos = yaml.safe_load(COMPOSE.read_text())
    assert isinstance(datos, dict)
    return datos


def _imagen_caddy() -> str:
    return str(_compose()["services"]["caddy"]["image"])


def test_caddyfile_pisa_y_devuelve_el_request_id() -> None:
    texto = CADDYFILE.read_text()
    assert "request_header X-Request-ID {http.request.uuid}" in texto
    assert "header X-Request-ID {http.request.uuid}" in texto


def test_compose_pasa_la_url_interna_de_la_api_a_la_web() -> None:
    web = _compose()["services"]["web"]
    assert web["environment"]["PROPTECH_URL_API_INTERNA"] == "http://api:8000"


def _caddy_adapt_validate() -> dict[str, Any]:
    """Corre `caddy adapt --validate` con la imagen de Caddy que usa Compose
    (D12: nunca una imagen escrita a mano) y devuelve el JSON adaptado."""
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


def test_caddy_adapt_validate_acepta_el_caddyfile() -> None:
    adaptado = _caddy_adapt_validate()
    assert adaptado.get("apps", {}).get("http") is not None


def test_el_json_adaptado_lleva_los_dos_filtros_del_logger_por_defecto() -> None:
    adaptado = _caddy_adapt_validate()
    campos = adaptado["logging"]["logs"]["default"]["encoder"]["fields"]
    assert campos["request>uri"]["filter"] == "delete"
    assert campos["request>headers"]["filter"] == "delete"
