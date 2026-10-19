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

import pytest


@pytest.mark.parametrize("variable", ["POSTGRES_APP_PASSWORD", "PROPTECH_PARAMETROS"])
def test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion(variable: str) -> None:
    """D13: importar es seguro aun sin configuración; la fábrica valida al arrancar."""
    entorno = dict(os.environ)
    entorno.pop(variable, None)

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_api.app; print('IMPORTADO')"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout == "IMPORTADO\n", resultado.stdout
    assert resultado.stderr == "", resultado.stderr


def test_el_proceso_termina_si_falta_postgres_app_password() -> None:
    """D3 (cambio 2a): `Configuracion` (la que usa la API) lee el par del rol de la
    app, `POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD`, no el del rol de arranque."""
    entorno = dict(os.environ)
    entorno.pop("POSTGRES_APP_PASSWORD", None)
    entorno.setdefault("POSTGRES_HOST", "db")
    entorno.setdefault("POSTGRES_PORT", "5432")
    entorno.setdefault("POSTGRES_APP_USER", "proptech_app")
    entorno.setdefault("POSTGRES_DB", "proptech")

    resultado = subprocess.run(
        [sys.executable, "-c", "from proptech_api.app import crear_app; crear_app()"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, (
        "el proceso arrancó (código 0) sin POSTGRES_APP_PASSWORD; "
        f"stdout={resultado.stdout!r} stderr={resultado.stderr!r}"
    )
    assert "POSTGRES_APP_PASSWORD" in resultado.stderr, (
        f"el error no nombra la variable faltante: {resultado.stderr!r}"
    )
