"""Ataque vuelta 3 (F12; D7, D13, L-007): el worker que arranca sin poder
llegar a Redis escribe 5 líneas en texto plano (`redis connection error
<host>:<puerto> ConnectionError <mensaje de redis-py>`) más un traceback
crudo final, porque `arq/connections.py:create_pool` corre ANTES del
`on_startup` del worker (que es donde `ajustes.py` reconfigura los logs si
el CLI los pisó) y el CLI de ARQ (`arq/cli.py`) hace
`logging.config.dictConfig(default_log_config(...))` justo después de
importar `proptech_worker.ajustes` (que ya llamó `configurar_logs` al
importarse) y antes de que `main()` intente conectar.

No usa contenedores: ni Redis (deliberadamente inalcanzable) ni PostgreSQL
(`Configuracion()` sólo valida el FORMATO de las variables, nunca se llega a
conectar).
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracion

RAIZ = Path(__file__).resolve().parents[3]
#: Nunca resuelve (dominio reservado para documentación/pruebas, RFC 2606):
#: el marcador de la vuelta 2 usaba uno parecido, F12 necesita el propio para
#: no pisar su aserción.
HOST_REDIS_INALCANZABLE = "marcador-f12-sin-redis.invalid"


def test_worker_sin_redis_no_repite_el_error_de_redis_py() -> None:
    entorno = {
        **os.environ,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "u",
        "POSTGRES_PASSWORD": "p",
        "POSTGRES_DB": "d",
        "REDIS_HOST": HOST_REDIS_INALCANZABLE,
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "x",
        "PROPTECH_PARAMETROS": str(RAIZ / "config" / "parametros.yaml"),
    }
    proceso = subprocess.run(
        # Exactamente el `command` del servicio `worker` de Compose (D2,
        # tarea 5.10): sin `--custom-log-dict`, el arreglo de F12 pisa
        # `arq.cli.default_log_config` al importar `ajustes.py`, no depende
        # de un flag extra en la línea de comandos.
        ["uv", "run", "arq", "proptech_worker.ajustes.AjustesDelWorker"],
        cwd=RAIZ / "backend",
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
    )
    salida = proceso.stdout + proceso.stderr

    assert HOST_REDIS_INALCANZABLE not in salida

    lineas = [linea for linea in salida.splitlines() if linea.strip()]
    assert lineas, "el worker no escribió nada: el test no prueba nada"
    no_json = []
    for linea in lineas:
        try:
            json.loads(linea)
        except json.JSONDecodeError:
            no_json.append(linea)
    assert no_json == [], f"líneas que no son JSON: {no_json[:5]}"
