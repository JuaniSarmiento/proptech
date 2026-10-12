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


def test_healthcheck_db_usa_variables_del_contenedor_entrecomilladas() -> None:
    """D-051/D11: el healthcheck debe leer POSTGRES_USER y POSTGRES_DB del entorno
    del propio contenedor (ya seteados en `environment:`), entrecomillados, en vez
    de re-interpolar con sintaxis de Compose sin comillas (rompe con espacios o
    valores vacíos, L-002)."""
    servicios = _compose()["services"]
    test = servicios["db"]["healthcheck"]["test"]
    comando = test[-1] if isinstance(test, list) else test
    assert 'pg_isready -U "$${POSTGRES_USER}" -d "$${POSTGRES_DB}"' in comando, comando


# --- 6.2: el stack arranca de verdad (D11/D6) ---


def test_api_recibe_variables_de_redis_obligatorias() -> None:
    """La API (D11) exige REDIS_HOST, REDIS_PORT y REDIS_PASSWORD; Compose
    tiene que pasárselas, la contraseña con obligatoriedad (`:?`) igual que
    las de PostgreSQL (sin Redis desplegado todavía en 1b, nadie se conecta:
    sólo se valida la forma de la variable)."""
    entorno = _compose()["services"]["api"]["environment"]
    assert entorno.get("REDIS_HOST")
    assert entorno.get("REDIS_PORT")
    assert "REDIS_PASSWORD:?" in str(entorno.get("REDIS_PASSWORD", "")).replace(" ", "")


def test_api_recibe_la_ruta_de_parametros_y_monta_config_de_solo_lectura() -> None:
    """D6: `PROPTECH_PARAMETROS=/app/config/parametros.yaml` y `config/` montada
    de sólo lectura, para que el lector encuentre el archivo del repositorio."""
    api = _compose()["services"]["api"]
    assert api["environment"].get("PROPTECH_PARAMETROS") == "/app/config/parametros.yaml"
    volumenes = [str(v) for v in api.get("volumes", [])]
    assert any("../config:/app/config:ro" in v for v in volumenes), volumenes


def test_migraciones_no_recibe_variables_de_redis_ni_parametros() -> None:
    """D11, tarea 6.1: el trabajo de migraciones sólo necesita PostgreSQL."""
    entorno = _compose()["services"]["migraciones"].get("environment", {})
    variables_de_mas = [clave for clave in entorno if clave.startswith("REDIS_")]
    assert variables_de_mas == [], variables_de_mas
    assert "PROPTECH_PARAMETROS" not in entorno


def test_env_example_tiene_redis_password() -> None:
    """`.env.example` tiene que traer `REDIS_PASSWORD`, si no `${REDIS_PASSWORD:?...}`
    deja sin arrancar a quien copie el archivo y no sepa que falta (D11)."""
    texto = (RAIZ / "infra" / ".env.example").read_text()
    assert "REDIS_PASSWORD=" in texto
