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


# --- 4.1: servicio Redis (D1) ---


def test_redis_imagen_8_10_2_trixie() -> None:
    servicios = _compose()["services"]
    assert "redis" in servicios, "falta el servicio redis"
    assert servicios["redis"]["image"] == "redis:8.10.2-trixie"


def test_redis_solo_en_red_interna_sin_ports() -> None:
    datos = _compose()
    redis = datos["services"]["redis"]
    assert "ports" not in redis, "redis no debe publicar puertos hacia el host"
    redes = redis.get("networks")
    assert redes == ["interna"] or redes == {"interna": None} or list(redes) == ["interna"], redes


def test_redis_volumen_con_nombre_datos_redis_en_slash_data() -> None:
    datos = _compose()
    assert "datos_redis" in datos.get("volumes", {}), "falta el volumen con nombre datos_redis"
    volumenes = [str(v) for v in datos["services"]["redis"].get("volumes", [])]
    assert any("datos_redis:/data" in v for v in volumenes), volumenes


def test_redis_command_appendonly_y_maxmemory_policy_noeviction() -> None:
    comando = _compose()["services"]["redis"]["command"]
    texto = " ".join(comando) if isinstance(comando, list) else str(comando)
    assert "--appendonly" in texto and "yes" in texto, texto
    assert "--maxmemory-policy noeviction" in texto, texto


def test_redis_command_requirepass_obligatoria_y_primer_argumento_redis_server() -> None:
    comando = _compose()["services"]["redis"]["command"]
    assert isinstance(comando, list), comando
    assert comando[0] == "redis-server", (
        f"el primer argumento debe ser redis-server (así el entrypoint baja a uid redis), "
        f"es {comando[0]!r}"
    )
    texto = " ".join(comando)
    assert "--requirepass" in texto, texto
    assert "REDIS_PASSWORD:?" in texto.replace(" ", ""), texto


def test_redis_healthcheck_con_rediscli_auth_y_doble_dolar() -> None:
    healthcheck = _compose()["services"]["redis"]["healthcheck"]
    test = healthcheck["test"]
    comando = test[-1] if isinstance(test, list) else test
    assert "REDISCLI_AUTH=" in comando, comando
    assert "$${REDIS_PASSWORD}" in comando, comando


# --- 5.10: servicio worker y su red de salida (D2, M18) ---


def test_worker_usa_la_imagen_de_api_con_comando_arq() -> None:
    servicios = _compose()["services"]
    assert "worker" in servicios, "falta el servicio worker"
    worker = servicios["worker"]
    api = servicios["api"]
    assert worker.get("image") == "proptech-backend:local"
    assert worker.get("image") == api.get("image")
    comando = worker.get("command")
    comando_texto = " ".join(comando) if isinstance(comando, list) else str(comando)
    assert comando_texto == "arq proptech_worker.ajustes.AjustesDelWorker"


def test_worker_healthcheck_arq_check() -> None:
    healthcheck = _compose()["services"]["worker"]["healthcheck"]
    test = healthcheck["test"]
    comando_texto = " ".join(test) if isinstance(test, list) else str(test)
    assert "arq" in comando_texto and "--check" in comando_texto, comando_texto
    assert "proptech_worker.ajustes.AjustesDelWorker" in comando_texto


def test_worker_sin_ports() -> None:
    worker = _compose()["services"]["worker"]
    assert "ports" not in worker, "worker no debe publicar puertos hacia el host"


def test_worker_en_red_interna_y_en_salida_worker_sin_internal() -> None:
    datos = _compose()
    worker = datos["services"]["worker"]
    redes = worker.get("networks")
    nombres_redes = set(redes)
    assert nombres_redes == {"interna", "salida_worker"}, nombres_redes

    assert "salida_worker" in datos["networks"], "falta declarar la red salida_worker"
    salida_worker = datos["networks"]["salida_worker"] or {}
    assert salida_worker.get("internal") is not True


def test_salida_worker_no_tiene_ningun_otro_servicio() -> None:
    """M18: ni la base, ni Redis, ni la API están en `salida_worker` (si no,
    quedarían alcanzables desde una red con salida a Internet)."""
    servicios = _compose()["services"]
    for nombre in ("db", "redis", "api"):
        redes = servicios[nombre].get("networks", [])
        nombres_redes = set(redes)
        assert "salida_worker" not in nombres_redes, f"{nombre} está en salida_worker"


def test_worker_depende_de_db_y_redis_saludables_y_migraciones_completado() -> None:
    depends_on = _compose()["services"]["worker"].get("depends_on", {})
    for nombre in ("db", "redis"):
        assert nombre in depends_on, f"worker no depende de {nombre}"
        condicion = depends_on[nombre]
        assert isinstance(condicion, dict) and condicion.get("condition") == "service_healthy"
    assert "migraciones" in depends_on
    condicion_migraciones = depends_on["migraciones"]
    assert (
        isinstance(condicion_migraciones, dict)
        and condicion_migraciones.get("condition") == "service_completed_successfully"
    )


def test_worker_monta_config_de_solo_lectura_y_recibe_parametros_y_redis() -> None:
    worker = _compose()["services"]["worker"]
    assert worker["environment"].get("PROPTECH_PARAMETROS") == "/app/config/parametros.yaml"
    volumenes = [str(v) for v in worker.get("volumes", [])]
    assert any("../config:/app/config:ro" in v for v in volumenes), volumenes

    entorno = worker["environment"]
    assert entorno.get("REDIS_HOST")
    assert entorno.get("REDIS_PORT")
    assert "REDIS_PASSWORD:?" in str(entorno.get("REDIS_PASSWORD", "")).replace(" ", "")
    assert "POSTGRES_PASSWORD:?" in str(entorno.get("POSTGRES_PASSWORD", "")).replace(" ", "")


def test_worker_tiene_ancla_de_rotacion_de_logs() -> None:
    worker = _compose()["services"]["worker"]
    assert "logging" in worker, "worker no declara rotación de logs (x-logs)"
    assert worker["logging"]["driver"] == "json-file"
