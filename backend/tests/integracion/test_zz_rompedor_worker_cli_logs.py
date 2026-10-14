"""Ataque del rompedor (vuelta 2, F1; D7, M25, 5.7): el worker de Compose
arranca con el CLI `arq proptech_worker.ajustes.AjustesDelWorker`. El CLI
importa los ajustes (que llaman a `configurar_logs("worker")` al
importarse) y DESPUÉS hace `logging.config.dictConfig(default_log_config(...))`,
que reemplaza el handler del logger `arq` (y de la raíz) por uno de texto
plano con el mensaje interpolado. La 5.7 corre el worker en proceso
(`arq.Worker`) y no pasa por ese camino.
"""

import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from arq.connections import RedisSettings
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

from proptech_core.compartido.cola import AdaptadorColaArq

from ..conftest import REDIS_PASSWORD_DE_PRUEBA

pytestmark = pytest.mark.integracion

RAIZ = Path(__file__).resolve().parents[3]
#: Corto y con clave corta: ARQ trunca los argumentos a ~80 caracteres.
MARCADOR = "m7d1e@x.invalid"


@pytest.mark.anyio
async def test_el_worker_por_el_cli_de_arq_escribe_solo_json_y_sin_argumentos(
    postgres_contenedor: PostgresContainer,
    redis_contenedor: DockerContainer,
    esquema_migrado: None,
) -> None:
    redis_host = redis_contenedor.get_container_host_ip()
    redis_port = int(redis_contenedor.get_exposed_port(6379))
    cola_pool = AdaptadorColaArq(
        RedisSettings(host=redis_host, port=redis_port, password=REDIS_PASSWORD_DE_PRUEBA)
    )
    await cola_pool.encolar(
        "tarea_de_prueba",
        clave=f"c{uuid.uuid4().hex[:6]}",
        request_id=str(uuid.uuid4()),
        fallar_veces=0,
        email=MARCADOR,
    )

    entorno = {
        **os.environ,
        "POSTGRES_HOST": postgres_contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(postgres_contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": postgres_contenedor.username,
        "POSTGRES_PASSWORD": postgres_contenedor.password,
        "POSTGRES_DB": postgres_contenedor.dbname,
        "REDIS_HOST": redis_host,
        "REDIS_PORT": str(redis_port),
        "REDIS_PASSWORD": REDIS_PASSWORD_DE_PRUEBA,
        "PROPTECH_PARAMETROS": str(RAIZ / "config" / "parametros.yaml"),
    }
    proceso = subprocess.run(
        ["uv", "run", "arq", "--burst", "proptech_worker.ajustes.AjustesDelWorker"],
        cwd=RAIZ / "backend",
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
    )
    salida = proceso.stdout + proceso.stderr

    assert MARCADOR not in salida
    lineas = [linea for linea in salida.splitlines() if linea.strip()]
    assert lineas, "el worker no escribió nada: el test no prueba nada"
    no_json = []
    for linea in lineas:
        try:
            json.loads(linea)
        except json.JSONDecodeError:
            no_json.append(linea)
    # `Worker.main()` (arq/worker.py) loguea estas DOS líneas fijas, sin
    # datos ("Starting worker for %d functions: %s" y el resumen de
    # `log_redis_info`) ANTES de llamar a `on_startup` donde recién
    # corremos `configurar_logs` de nuevo (D7): no hay un hook de ARQ que
    # corra antes de esas dos líneas y después del `dictConfig` del CLI.
    # Ninguna de las dos lleva el nombre de la tarea con sus argumentos ni
    # ningún dato (sólo la cantidad de funciones y métricas genéricas de
    # Redis), así que se tolera sólo esa forma exacta; cualquier otra línea
    # no-JSON sigue haciendo fallar el test.
    no_json_inesperadas = [
        linea
        for linea in no_json
        if "Starting worker for" not in linea and "redis_version=" not in linea
    ]
    assert no_json_inesperadas == [], f"líneas que no son JSON: {no_json_inesperadas[:3]}"


@pytest.mark.anyio
async def test_el_worker_por_el_cli_de_arq_tambien_loguea_en_json_un_reintento(
    postgres_contenedor: PostgresContainer,
    redis_contenedor: DockerContainer,
    esquema_migrado: None,
) -> None:
    """Triangula el caso anterior: no sólo el trabajo feliz, también el
    camino de reintento (`reintento_programado`, D3) tiene que quedar en
    JSON por el CLI, no sólo cuando se corre `arq.Worker` en proceso (5.3)."""
    redis_host = redis_contenedor.get_container_host_ip()
    redis_port = int(redis_contenedor.get_exposed_port(6379))
    cola_pool = AdaptadorColaArq(
        RedisSettings(host=redis_host, port=redis_port, password=REDIS_PASSWORD_DE_PRUEBA)
    )
    await cola_pool.encolar(
        "tarea_de_prueba",
        clave=f"r{uuid.uuid4().hex[:6]}",
        request_id=str(uuid.uuid4()),
        fallar_veces=1,
        email=MARCADOR,
    )

    entorno = {
        **os.environ,
        "POSTGRES_HOST": postgres_contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(postgres_contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": postgres_contenedor.username,
        "POSTGRES_PASSWORD": postgres_contenedor.password,
        "POSTGRES_DB": postgres_contenedor.dbname,
        "REDIS_HOST": redis_host,
        "REDIS_PORT": str(redis_port),
        "REDIS_PASSWORD": REDIS_PASSWORD_DE_PRUEBA,
        "PROPTECH_PARAMETROS": str(RAIZ / "config" / "parametros.yaml"),
    }
    proceso = subprocess.run(
        ["uv", "run", "arq", "--burst", "proptech_worker.ajustes.AjustesDelWorker"],
        cwd=RAIZ / "backend",
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
    )
    salida = proceso.stdout + proceso.stderr

    assert MARCADOR not in salida
    lineas = [linea for linea in salida.splitlines() if linea.strip()]
    eventos = []
    no_json_inesperadas = []
    for linea in lineas:
        try:
            eventos.append(json.loads(linea))
        except json.JSONDecodeError:
            if "Starting worker for" not in linea and "redis_version=" not in linea:
                no_json_inesperadas.append(linea)
    assert no_json_inesperadas == [], f"líneas que no son JSON: {no_json_inesperadas[:3]}"
    assert any(evento.get("evento") == "reintento_programado" for evento in eventos), eventos
