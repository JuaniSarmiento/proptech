"""Arranque de la API (D11 / spec "API sin cadena de conexión").

Si falta una variable de configuración, el proceso tiene que terminar al
arrancar, nombrando la variable que falta y sin mostrar ningún valor secreto.
Lo que NO debe pasar: que la API arranque igual y recién en el primer pedido
a /api/salud se entere, respondiendo 503 "sin_conexion" como si la base
estuviera caída (un error de configuración disfrazado de base caída).
"""

import os
import subprocess
import sys


def test_el_proceso_termina_si_falta_postgres_password() -> None:
    entorno = dict(os.environ)
    entorno.pop("POSTGRES_PASSWORD", None)
    entorno.setdefault("POSTGRES_HOST", "db")
    entorno.setdefault("POSTGRES_PORT", "5432")
    entorno.setdefault("POSTGRES_USER", "proptech")
    entorno.setdefault("POSTGRES_DB", "proptech")

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_api.app"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, (
        "el proceso arrancó (código 0) sin POSTGRES_PASSWORD; "
        f"stdout={resultado.stdout!r} stderr={resultado.stderr!r}"
    )
    assert "POSTGRES_PASSWORD" in resultado.stderr, (
        f"el error no nombra la variable faltante: {resultado.stderr!r}"
    )
