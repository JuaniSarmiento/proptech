"""Tests estáticos sobre infra/compose.yaml: red, puertos y dependencias (D8/D9)."""

from pathlib import Path
from typing import Any

import pytest
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


def test_db_solo_en_red_datos_y_es_internal() -> None:
    """D10 (cambio 2a): `interna` se partió en `datos` (db, redis, migraciones,
    api, worker, respaldos) y `aplicacion` (api, web, caddy)."""
    datos = _compose()
    redes_db = datos["services"]["db"].get("networks")
    assert list(redes_db) == ["datos"], redes_db
    assert datos["networks"]["datos"].get("internal") is True


def test_migraciones_corre_roles_antes_alembic_y_roles_despues_en_orden() -> None:
    """D1, D2 (cambio 2a, tarea 2.3): el paso de roles antes y después de
    Alembic, en ese orden, con `&&` (si uno falla, no sigue el siguiente)."""
    servicios = _compose()["services"]
    api = servicios["api"]
    migraciones = servicios["migraciones"]
    assert migraciones.get("image") == api.get("image") or migraciones.get("build") == api.get(
        "build"
    )
    comando = migraciones.get("command")
    comando_texto = " ".join(comando) if isinstance(comando, list) else str(comando)
    pos_antes = comando_texto.find("proptech_core.compartido.roles antes")
    pos_alembic = comando_texto.find("alembic upgrade head")
    pos_despues = comando_texto.find("proptech_core.compartido.roles despues")
    assert pos_antes != -1, comando_texto
    assert pos_alembic != -1, comando_texto
    assert pos_despues != -1, comando_texto
    assert pos_antes < pos_alembic < pos_despues, comando_texto
    assert "&&" in comando_texto, "si un paso falla, el siguiente no debe correr"
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


def test_redis_solo_en_red_datos_sin_ports() -> None:
    datos = _compose()
    redis = datos["services"]["redis"]
    assert "ports" not in redis, "redis no debe publicar puertos hacia el host"
    redes = redis.get("networks")
    assert list(redes) == ["datos"], redes


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


def test_worker_en_red_datos_y_en_salida_worker_sin_internal() -> None:
    datos = _compose()
    worker = datos["services"]["worker"]
    redes = worker.get("networks")
    nombres_redes = set(redes)
    assert nombres_redes == {"datos", "salida_worker"}, nombres_redes

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
    # D1, D3 (tarea 2.3): el worker usa el rol de la app, no el de arranque.
    assert "POSTGRES_APP_PASSWORD:?" in str(entorno.get("POSTGRES_APP_PASSWORD", "")).replace(
        " ", ""
    )
    assert "POSTGRES_PASSWORD" not in entorno


def test_worker_tiene_ancla_de_rotacion_de_logs() -> None:
    worker = _compose()["services"]["worker"]
    assert "logging" in worker, "worker no declara rotación de logs (x-logs)"
    assert worker["logging"]["driver"] == "json-file"


# --- 4.1: servicio respaldos (D9, cambio 1d) ---


def test_respaldos_imagen_igual_a_la_de_db() -> None:
    servicios = _compose()["services"]
    assert "respaldos" in servicios, "falta el servicio respaldos"
    assert servicios["respaldos"]["image"] == servicios["db"]["image"]


def test_respaldos_solo_en_red_datos_y_sin_ports() -> None:
    servicios = _compose()["services"]
    respaldos = servicios["respaldos"]
    assert "ports" not in respaldos, "respaldos no debe publicar puertos hacia el host"
    redes = respaldos.get("networks")
    nombres_redes = set(redes)
    assert nombres_redes == {"datos"}, nombres_redes


def test_respaldos_usuario_desde_proptech_uid_gid_con_obligatoriedad() -> None:
    respaldos = _compose()["services"]["respaldos"]
    usuario = str(respaldos.get("user", ""))
    assert "PROPTECH_UID:?" in usuario.replace(" ", "")
    assert "PROPTECH_GID:?" in usuario.replace(" ", "")


def test_respaldos_monta_carpeta_del_host_como_bind_con_obligatoriedad() -> None:
    respaldos = _compose()["services"]["respaldos"]
    volumenes = [str(v) for v in respaldos.get("volumes", [])]
    monta_carpeta = [v for v in volumenes if "/respaldos" in v and "respaldar.sh" not in v]
    assert monta_carpeta, f"no se encontró el bind mount de la carpeta: {volumenes}"
    assert any("PROPTECH_DIR_RESPALDOS:?" in v.replace(" ", "") for v in monta_carpeta), (
        monta_carpeta
    )
    # No tiene que ser un volumen CON NOMBRE (L-006/D9: `down -v` se lo
    # llevaría junto con la base).
    datos = _compose()
    for nombre_volumen in datos.get("volumes", {}):
        assert nombre_volumen not in " ".join(monta_carpeta), (
            f"la carpeta de respaldos no puede ser un volumen con nombre: {nombre_volumen}"
        )


def test_respaldos_monta_el_script_de_solo_lectura_como_entrypoint() -> None:
    respaldos = _compose()["services"]["respaldos"]
    entrypoint = respaldos.get("entrypoint")
    texto_entrypoint = " ".join(entrypoint) if isinstance(entrypoint, list) else str(entrypoint)
    assert "respaldar.sh" in texto_entrypoint, texto_entrypoint

    volumenes = [str(v) for v in respaldos.get("volumes", [])]
    monta_script = [v for v in volumenes if "respaldar.sh" in v]
    assert monta_script, f"no se encontró el montaje del script: {volumenes}"
    assert all(v.endswith(":ro") for v in monta_script), monta_script


def test_respaldos_depende_de_db_saludable_y_migraciones_completado() -> None:
    depends_on = _compose()["services"]["respaldos"].get("depends_on", {})
    assert "db" in depends_on
    condicion_db = depends_on["db"]
    assert isinstance(condicion_db, dict) and condicion_db.get("condition") == "service_healthy"
    assert "migraciones" in depends_on
    condicion_migraciones = depends_on["migraciones"]
    assert (
        isinstance(condicion_migraciones, dict)
        and condicion_migraciones.get("condition") == "service_completed_successfully"
    )


def test_respaldos_healthcheck_con_salud_y_start_period() -> None:
    healthcheck = _compose()["services"]["respaldos"]["healthcheck"]
    test = healthcheck["test"]
    comando_texto = " ".join(test) if isinstance(test, list) else str(test)
    assert "--salud" in comando_texto, comando_texto
    assert "start_period" in healthcheck, healthcheck


def test_respaldos_tiene_ancla_de_rotacion_de_logs() -> None:
    respaldos = _compose()["services"]["respaldos"]
    assert "logging" in respaldos, "respaldos no declara rotación de logs (x-logs)"
    assert respaldos["logging"]["driver"] == "json-file"


def test_respaldos_recibe_las_variables_respaldo() -> None:
    entorno = _compose()["services"]["respaldos"].get("environment", {})
    for variable in (
        "RESPALDO_INTERVALO_SEGUNDOS",
        "RESPALDO_CONSERVAR",
        "RESPALDO_LIMITE_SEGUNDOS",
    ):
        assert variable in entorno, f"falta la variable {variable} en el servicio respaldos"


def test_respaldos_no_esta_en_la_red_de_salida_del_worker() -> None:
    respaldos = _compose()["services"]["respaldos"]
    redes = set(respaldos.get("networks", []))
    assert "salida_worker" not in redes, redes


# --- 4.2: configuración del repositorio para los respaldos (D9, cambio 1d) ---


def _entorno_compose_valido() -> dict[str, str]:
    import os

    entorno = dict(os.environ)
    entorno.update(
        {
            "POSTGRES_USER": "proptech",
            "POSTGRES_PASSWORD": "valor-de-prueba-no-real",
            "POSTGRES_MIGRADOR_USER": "proptech_migrador",
            "POSTGRES_MIGRADOR_PASSWORD": "valor-de-prueba-no-real",
            "POSTGRES_APP_USER": "proptech_app",
            "POSTGRES_APP_PASSWORD": "valor-de-prueba-no-real",
            "POSTGRES_RESPALDO_USER": "proptech_respaldo",
            "POSTGRES_RESPALDO_PASSWORD": "valor-de-prueba-no-real",
            "POSTGRES_DB": "proptech",
            "REDIS_PASSWORD": "valor-de-prueba-no-real",
            "PROPTECH_SITIO": "http://localhost",
            "PROPTECH_DIR_RESPALDOS": "./datos-respaldos-de-prueba",
            "PROPTECH_UID": "1000",
            "PROPTECH_GID": "1000",
        }
    )
    return entorno


def test_gitignore_ignora_la_carpeta_de_respaldos() -> None:
    import subprocess

    carpeta = RAIZ / "infra" / "datos-respaldos"
    carpeta.mkdir(exist_ok=True)
    archivo_de_prueba = carpeta / "proptech-20261014T000000Z.dump"
    archivo_de_prueba.write_text("contenido-de-prueba, no un backup real")
    try:
        resultado = subprocess.run(
            ["git", "check-ignore", "-q", str(archivo_de_prueba)],
            cwd=str(RAIZ),
            check=False,
        )
        assert resultado.returncode == 0, (
            "git no ignora infra/datos-respaldos/: el backup de prueba se versionaría"
        )
    finally:
        archivo_de_prueba.unlink()
        carpeta.rmdir()


def test_env_example_trae_las_variables_de_respaldos() -> None:
    texto = (RAIZ / "infra" / ".env.example").read_text()
    for variable in (
        "PROPTECH_DIR_RESPALDOS",
        "PROPTECH_UID",
        "PROPTECH_GID",
        "RESPALDO_INTERVALO_SEGUNDOS",
        "RESPALDO_CONSERVAR",
        "RESPALDO_LIMITE_SEGUNDOS",
    ):
        assert f"{variable}=" in texto, f"falta {variable} en infra/.env.example"


@pytest.mark.parametrize(
    "variable_faltante",
    ["PROPTECH_DIR_RESPALDOS", "PROPTECH_UID", "PROPTECH_GID"],
)
def test_compose_config_falla_sin_variable_obligatoria_de_respaldos(
    variable_faltante: str,
) -> None:
    import subprocess

    entorno = _entorno_compose_valido()
    entorno.pop(variable_faltante, None)

    resultado = subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        cwd=str(RAIZ / "infra"),
        env=entorno,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert resultado.returncode != 0, f"docker compose config debía fallar sin {variable_faltante}"
    assert variable_faltante in resultado.stderr, resultado.stderr


# --- 2.3: credenciales por rol (D1, D3) ---


def test_api_tiene_las_variables_de_la_app_y_no_las_de_otro_rol() -> None:
    entorno = _compose()["services"]["api"]["environment"]
    assert "POSTGRES_APP_USER:?" in str(entorno.get("POSTGRES_APP_USER", "")).replace(" ", "")
    assert "POSTGRES_APP_PASSWORD:?" in str(entorno.get("POSTGRES_APP_PASSWORD", "")).replace(
        " ", ""
    )
    for variable in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_MIGRADOR_PASSWORD",
        "POSTGRES_RESPALDO_PASSWORD",
    ):
        assert variable not in entorno, f"la API no debería tener {variable}"


def test_worker_tiene_las_variables_de_la_app_y_no_las_de_otro_rol() -> None:
    entorno = _compose()["services"]["worker"]["environment"]
    for variable in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_MIGRADOR_PASSWORD",
        "POSTGRES_RESPALDO_PASSWORD",
    ):
        assert variable not in entorno, f"el worker no debería tener {variable}"


def test_respaldos_usa_pguser_del_rol_de_respaldo_y_no_tiene_postgres_password() -> None:
    respaldos = _compose()["services"]["respaldos"]
    entorno = respaldos.get("environment", {})
    assert "POSTGRES_RESPALDO_USER:?" in str(entorno.get("PGUSER", "")).replace(" ", "")
    assert "POSTGRES_RESPALDO_PASSWORD:?" in str(entorno.get("PGPASSWORD", "")).replace(" ", "")
    assert "POSTGRES_PASSWORD" not in str(entorno.get("PGPASSWORD", ""))
    assert "POSTGRES_PASSWORD" not in entorno


def test_migraciones_tiene_los_cuatro_pares_de_credenciales() -> None:
    """El paso de roles (D2) necesita, con el rol de arranque, leer el nombre y
    la contraseña que le va a dar a los otros tres."""
    entorno = _compose()["services"]["migraciones"]["environment"]
    for par in (
        ("POSTGRES_USER", "POSTGRES_PASSWORD"),
        ("POSTGRES_MIGRADOR_USER", "POSTGRES_MIGRADOR_PASSWORD"),
        ("POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD"),
        ("POSTGRES_RESPALDO_USER", "POSTGRES_RESPALDO_PASSWORD"),
    ):
        for variable in par:
            assert f"{variable}:?" in str(entorno.get(variable, "")).replace(" ", ""), variable


def test_ningun_servicio_permanente_tiene_la_password_de_arranque() -> None:
    """D1: "ningún servicio permanente tiene la contraseña del rol de
    arranque". `db` queda exceptuado a propósito: ES el rol de arranque (la
    imagen oficial lo crea con esas variables); `migraciones` también, porque
    es de una sola corrida (`restart: "no"`), no un servicio permanente."""
    servicios = _compose()["services"]
    permanentes_exceptuados = {"db", "migraciones"}
    for nombre, servicio in servicios.items():
        if nombre in permanentes_exceptuados:
            continue
        if servicio.get("restart") == "no":
            continue
        entorno = servicio.get("environment", {}) or {}
        assert "POSTGRES_PASSWORD" not in entorno, f"{nombre} tiene POSTGRES_PASSWORD"


# --- 2.3: la web fuera de la red de la base (D10) ---


def test_web_no_esta_en_ninguna_red_con_db_ni_redis() -> None:
    datos = _compose()
    redes_de_db = set(datos["services"]["db"].get("networks", []))
    redes_de_redis = set(datos["services"]["redis"].get("networks", []))
    redes_de_web = set(datos["services"]["web"].get("networks", []))
    assert not (redes_de_web & redes_de_db), redes_de_web & redes_de_db
    assert not (redes_de_web & redes_de_redis), redes_de_web & redes_de_redis


def test_caddy_tiene_ip_fija_en_aplicacion_y_coincide_con_forwarded_allow_ips() -> None:
    datos = _compose()
    caddy_redes = datos["services"]["caddy"]["networks"]
    assert "aplicacion" in caddy_redes, caddy_redes
    ip_de_caddy = caddy_redes["aplicacion"]["ipv4_address"]
    forwarded = str(_compose()["services"]["api"]["environment"]["FORWARDED_ALLOW_IPS"])
    assert ip_de_caddy in forwarded, (ip_de_caddy, forwarded)
    assert datos["networks"]["aplicacion"].get("internal") is True


def test_api_esta_en_datos_y_en_aplicacion() -> None:
    redes = set(_compose()["services"]["api"].get("networks", []))
    assert redes == {"datos", "aplicacion"}, redes


# --- 2.3: nunca --enable-row-security en infra/ (L-013, L-016) ---


def test_ningun_archivo_de_infra_contiene_enable_row_security() -> None:
    """D4 del design (lo probó el arquitecto): `pg_dump` como la app falla
    ruidoso; con `--enable-row-security` sale vacío y en silencio. Nadie en
    `infra/` debe agregar esa opción (sólo `proptech_respaldo`, con
    `BYPASSRLS`, hace los volcados, y no la necesita)."""
    for archivo in RAIZ.joinpath("infra").rglob("*"):
        if archivo.is_file():
            try:
                texto = archivo.read_text(encoding="utf-8")
            except UnicodeDecodeError, PermissionError:
                continue
            assert "--enable-row-security" not in texto, archivo


def test_rojo_con_una_copia_de_respaldar_que_agrega_enable_row_security(
    tmp_path: Path,
) -> None:
    """L-013: copia de `respaldar.sh` con la opción agregada a propósito, para
    ver el chequeo estático fallar por la razón correcta antes de confiar en
    que "no aparece" prueba algo."""
    original = RAIZ / "infra" / "respaldos" / "respaldar.sh"
    texto_real = original.read_text(encoding="utf-8")
    assert "--enable-row-security" not in texto_real

    texto_mutado = texto_real.replace(
        'pg_dump --format=custom "--file=${archivo_parcial}"',
        'pg_dump --enable-row-security --format=custom "--file=${archivo_parcial}"',
    )
    assert texto_mutado != texto_real, "no se encontró la línea exacta de pg_dump a mutar"

    copia = tmp_path / "respaldar_mutado.sh"
    copia.write_text(texto_mutado, encoding="utf-8")

    assert "--enable-row-security" in copia.read_text(encoding="utf-8")
    assert "--enable-row-security" not in original.read_text(encoding="utf-8")


def test_env_example_tiene_las_cuatro_contrasenas_distintas() -> None:
    """R8 (vuelta 2): copiar este archivo sin editar y correr `roles antes`
    tiene que arrancar — no chocar con el rechazo nuevo de dos contraseñas
    iguales (el archivo las traía las cuatro iguales antes de esto)."""
    texto = (RAIZ / "infra" / ".env.example").read_text()
    valores: dict[str, str] = {}
    for linea in texto.splitlines():
        for variable in (
            "POSTGRES_PASSWORD",
            "POSTGRES_MIGRADOR_PASSWORD",
            "POSTGRES_APP_PASSWORD",
            "POSTGRES_RESPALDO_PASSWORD",
        ):
            if linea.startswith(f"{variable}="):
                valores[variable] = linea.split("=", 1)[1]
    assert len(valores) == 4, f"faltan contraseñas en infra/.env.example: {valores.keys()}"
    assert len(set(valores.values())) == 4, (
        f"infra/.env.example tiene contraseñas repetidas: {valores}"
    )


def test_env_example_trae_los_cuatro_pares_de_credenciales() -> None:
    texto = (RAIZ / "infra" / ".env.example").read_text()
    for variable in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_MIGRADOR_USER",
        "POSTGRES_MIGRADOR_PASSWORD",
        "POSTGRES_APP_USER",
        "POSTGRES_APP_PASSWORD",
        "POSTGRES_RESPALDO_USER",
        "POSTGRES_RESPALDO_PASSWORD",
    ):
        assert f"{variable}=" in texto, f"falta {variable} en infra/.env.example"
