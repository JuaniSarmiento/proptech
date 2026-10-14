"""Gemelo de `test_arranque_api_password_vacio.py` (L-009). Cambio 1c,
tarea 5.9.

Una contraseña presente pero vacía (o en blanco) no es "falta" para
pydantic: la variable existe, sólo que vacía. Acá, además de
`POSTGRES_PASSWORD` (como en la API), se suma `REDIS_PASSWORD` vacía y en
blanco, específico del worker.
"""

import os
import subprocess
import sys


def test_el_proceso_no_arranca_con_postgres_password_vacio() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "5432"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = ""
    entorno["POSTGRES_DB"] = "proptech"

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes; print('ARRANCO')"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, (
        f"el proceso arrancó con POSTGRES_PASSWORD vacío. stdout={resultado.stdout!r}"
    )


def test_el_proceso_no_arranca_con_redis_password_vacia() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "5432"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = "proptech"
    entorno["POSTGRES_DB"] = "proptech"
    entorno["REDIS_HOST"] = "redis"
    entorno["REDIS_PORT"] = "6379"
    entorno["REDIS_PASSWORD"] = ""

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes; print('ARRANCO')"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, (
        f"el proceso arrancó con REDIS_PASSWORD vacía. stdout={resultado.stdout!r}"
    )
    assert "REDIS_PASSWORD" in resultado.stderr


def test_el_proceso_no_arranca_con_redis_password_en_blanco() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "5432"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = "proptech"
    entorno["POSTGRES_DB"] = "proptech"
    entorno["REDIS_HOST"] = "redis"
    entorno["REDIS_PORT"] = "6379"
    entorno["REDIS_PASSWORD"] = "   "

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes; print('ARRANCO')"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, (
        f"el proceso arrancó con REDIS_PASSWORD en blanco. stdout={resultado.stdout!r}"
    )
    assert "REDIS_PASSWORD" in resultado.stderr
