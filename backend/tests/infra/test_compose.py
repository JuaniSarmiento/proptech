"""Tests estáticos sobre infra/compose.yaml: red, puertos y dependencias (D8/D9)."""

from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "infra" / "compose.yaml"


def _compose() -> dict[str, Any]:
    datos = yaml.safe_load(COMPOSE.read_text())
    assert isinstance(datos, dict)
    return datos


def test_compose_declara_nombre_de_proyecto_fijo() -> None:
    """Sin `name:`, Compose usa el nombre de la carpeta (`infra`) como proyecto, y
    `docker compose down -v --remove-orphans` en `humo.sh` opera sobre ese nombre
    genérico: puede pisar o limpiar el stack de OTRO proyecto que también se llame
    `infra` en la misma máquina."""
    datos = _compose()
    assert datos.get("name") == "proptech"


def test_solo_caddy_publica_puertos_80_y_443() -> None:
    servicios = _compose()["services"]
    con_puertos = {nombre: s for nombre, s in servicios.items() if "ports" in s}
    assert set(con_puertos) == {"caddy"}, f"servicios con ports: {set(con_puertos)}"
    assert "80" in str(con_puertos["caddy"]["ports"])
    assert "443" in str(con_puertos["caddy"]["ports"])


def test_db_api_web_migraciones_sin_ports() -> None:
    servicios = _compose()["services"]
    for nombre in ("db", "api", "web", "migraciones"):
        assert nombre in servicios, f"falta el servicio {nombre}"
        assert "ports" not in servicios[nombre], f"{nombre} tiene ports publicados"


def test_db_solo_en_red_interna_y_es_internal() -> None:
    datos = _compose()
    redes_db = datos["services"]["db"].get("networks")
    assert redes_db == ["interna"] or redes_db == {"interna": None} or list(redes_db) == ["interna"]
    assert datos["networks"]["interna"].get("internal") is True


def test_migraciones_usa_la_imagen_de_api_con_comando_alembic_upgrade_head() -> None:
    servicios = _compose()["services"]
    api = servicios["api"]
    migraciones = servicios["migraciones"]
    assert migraciones.get("image") == api.get("image") or migraciones.get("build") == api.get(
        "build"
    )
    comando = migraciones.get("command")
    comando_texto = " ".join(comando) if isinstance(comando, list) else str(comando)
    assert "alembic" in comando_texto
    assert "upgrade" in comando_texto
    assert "head" in comando_texto
    assert migraciones.get("restart") == "no"


def test_api_depende_de_migraciones_completadas() -> None:
    servicios = _compose()["services"]
    depends_on = servicios["api"].get("depends_on", {})
    assert "migraciones" in depends_on
    condicion = depends_on["migraciones"]
    if isinstance(condicion, dict):
        assert condicion.get("condition") == "service_completed_successfully"
    else:
        raise AssertionError("depends_on.migraciones no declara condition")


def test_postgres_password_interpolada_con_obligatoriedad() -> None:
    texto = COMPOSE.read_text()
    assert "POSTGRES_PASSWORD:?" in texto.replace(" ", "")
