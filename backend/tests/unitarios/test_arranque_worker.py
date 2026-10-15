"""Arranque del worker (D11 / spec "Worker sin una variable obligatoria").
Gemelo de `test_arranque_api.py` (L-009). Cambio 1c, tarea 5.9.

Si falta una variable de configuración, el proceso tiene que terminar al
arrancar, nombrando la variable que falta y sin mostrar ningún valor
secreto.
"""

import os
import subprocess
import sys


def test_el_proceso_termina_si_falta_postgres_app_password() -> None:
    """D3 (cambio 2a): el worker usa `Configuracion`, el rol de la app."""
    entorno = dict(os.environ)
    entorno.pop("POSTGRES_APP_PASSWORD", None)
    entorno.setdefault("POSTGRES_HOST", "db")
    entorno.setdefault("POSTGRES_PORT", "5432")
    entorno.setdefault("POSTGRES_APP_USER", "proptech_app")
    entorno.setdefault("POSTGRES_DB", "proptech")

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
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
