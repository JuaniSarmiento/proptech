"""Gemelo de `test_arranque_api_variable_malformada.py` (L-009). Cambio 1c,
tarea 5.9.

Ataca el caso vecino al de "falta la variable": está PRESENTE pero MAL
FORMADA. Acá además de `POSTGRES_PORT=abc` (como en la API) se suma
`REDIS_PORT=abc` y `REDIS_PORT=70000` (fuera de rango), específicos del
worker.
"""

import os
import subprocess
import sys


def test_el_proceso_nombra_la_variable_con_postgres_port_malformado() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "abc"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = "proptech"
    entorno["POSTGRES_DB"] = "proptech"

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, "el proceso debería terminar con POSTGRES_PORT inválido"
    assert "POSTGRES_PORT" in resultado.stderr, (
        f"el error no nombra la variable rota: stderr={resultado.stderr!r}"
    )


def test_el_proceso_nombra_la_variable_con_redis_port_malformado() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "5432"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = "proptech"
    entorno["POSTGRES_DB"] = "proptech"
    entorno["REDIS_HOST"] = "redis"
    entorno["REDIS_PORT"] = "abc"
    entorno["REDIS_PASSWORD"] = "redis-pass"

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, "el proceso debería terminar con REDIS_PORT inválido"
    assert "REDIS_PORT" in resultado.stderr, (
        f"el error no nombra la variable rota: {resultado.stderr!r}"
    )
    assert "redis-pass" not in resultado.stderr


def test_el_proceso_nombra_la_variable_con_redis_port_fuera_de_rango() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "5432"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = "proptech"
    entorno["POSTGRES_DB"] = "proptech"
    entorno["REDIS_HOST"] = "redis"
    entorno["REDIS_PORT"] = "70000"
    entorno["REDIS_PASSWORD"] = "redis-pass"

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, "el proceso debería terminar con REDIS_PORT fuera de rango"
    assert "REDIS_PORT" in resultado.stderr, (
        f"el error no nombra la variable rota: {resultado.stderr!r}"
    )
    assert "redis-pass" not in resultado.stderr
