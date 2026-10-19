"""Tests estáticos de rotación de logs, confianza en el proxy y log de PostgreSQL
(D7, D17). Cambio 1c, tarea 2.3.

Escenarios de `entorno-de-ejecucion`: Rotación declarada; La API confía sólo en el
proxy. Escenario de `trazabilidad-y-logs`: Query string con un dato personal (sin
log de acceso de uvicorn).
"""

import ipaddress
import re
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "infra" / "compose.yaml"
DOCKERFILE_BACKEND = RAIZ / "backend" / "Dockerfile"


def _compose_crudo() -> str:
    return COMPOSE.read_text()


def _compose() -> dict[str, Any]:
    datos = yaml.safe_load(_compose_crudo())
    assert isinstance(datos, dict)
    return datos


def test_dockerfile_backend_corre_uvicorn_sin_log_de_acceso_y_confiando_en_el_proxy() -> None:
    texto = DOCKERFILE_BACKEND.read_text()
    coincidencia = re.search(r"^CMD\s+(\[.*\])\s*$", texto, flags=re.MULTILINE)
    assert coincidencia is not None, "no se encontró un CMD en backend/Dockerfile"
    comando = yaml.safe_load(coincidencia.group(1))
    assert comando[:3] == ["uvicorn", "--factory", "proptech_api.app:crear_app"], comando
    assert "--no-access-log" in comando, comando
    assert "--proxy-headers" in comando, comando


def test_red_aplicacion_declara_una_subred() -> None:
    """D10 (cambio 2a, tarea 2.3): `interna` se partió en `datos` y
    `aplicacion`; la subred fija (para la IP de Caddy) vive en `aplicacion`."""
    aplicacion = _compose()["networks"]["aplicacion"]
    subred = aplicacion["ipam"]["config"][0]["subnet"]
    # Verifica que sea una subred válida (lanza ValueError si no lo es).
    ipaddress.ip_network(subred)


def test_caddy_tiene_direccion_fija_dentro_de_la_subred_aplicacion() -> None:
    datos = _compose()
    subred = ipaddress.ip_network(datos["networks"]["aplicacion"]["ipam"]["config"][0]["subnet"])
    redes_caddy = datos["services"]["caddy"]["networks"]
    assert isinstance(redes_caddy, dict), "caddy debe declarar networks como mapeo para fijar IP"
    direccion_caddy = redes_caddy["aplicacion"]["ipv4_address"]
    assert ipaddress.ip_address(direccion_caddy) in subred


def test_api_confia_solo_en_la_direccion_fija_de_caddy() -> None:
    datos = _compose()
    direccion_caddy = datos["services"]["caddy"]["networks"]["aplicacion"]["ipv4_address"]
    forwarded = datos["services"]["api"]["environment"]["FORWARDED_ALLOW_IPS"]
    assert forwarded == direccion_caddy
    assert forwarded != "*"
    assert "/" not in str(forwarded), "FORWARDED_ALLOW_IPS no debe ser una subred entera"


def test_postgres_loguea_con_el_prefijo_que_lleva_el_application_name() -> None:
    comando = _compose()["services"]["db"].get("command")
    assert comando is not None, "el servicio db no declara command"
    comando_texto = " ".join(comando) if isinstance(comando, list) else str(comando)
    assert "log_line_prefix=%m [%p] %q%a " in comando_texto, comando_texto


def test_ancla_de_rotacion_aplicada_a_todos_los_servicios() -> None:
    datos = _compose()
    for nombre, servicio in datos["services"].items():
        logging_cfg = servicio.get("logging")
        assert logging_cfg is not None, f"{nombre} no tiene logging (ancla x-logs)"
        assert logging_cfg.get("driver") == "json-file", f"{nombre}: {logging_cfg}"
        opciones = logging_cfg.get("options", {})
        assert opciones.get("max-size"), f"{nombre} no fija max-size"
        assert opciones.get("max-file"), f"{nombre} no fija max-file"


def test_ancla_x_logs_se_reusa_en_vez_de_copiarse_por_servicio() -> None:
    """La configuración de rotación se escribe una sola vez bajo `x-logs` y
    cada servicio la reusa con una ancla YAML (`<<:`), en vez de repetir
    `max-size`/`max-file` copiados y pegados en cada uno."""
    texto = _compose_crudo()
    assert texto.count("x-logs:") == 1
    assert texto.count("max-size") == 1, "max-size está copiado en más de un lugar"
    assert texto.count("max-file") == 1, "max-file está copiado en más de un lugar"
