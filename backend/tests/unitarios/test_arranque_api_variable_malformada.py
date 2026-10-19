"""Regresión: encontrado por el Rompedor (ronda 2), movido desde `tests/rompedor/`.

Ataca el fix de "falla rápido nombrando la variable" (D11).

El fix cubre el caso "falta la variable" (pydantic la marca como `missing`).
Este test ataca el caso vecino, de la misma familia: la variable está PRESENTE
pero MAL FORMADA (p.ej. POSTGRES_PORT="abc", que no castea a int). Pydantic
la marca como `int_parsing`, no `missing`, así que el filtro de
`Configuracion.__init__` (`e["type"] == "missing"`) no la agarra y cae al
mensaje genérico "Configuración inválida" — que NO nombra la variable.

Un operador real, con 5 variables de Postgres, no sabe cuál mirar.
"""

import os
import subprocess
import sys


def test_el_proceso_nombra_la_variable_con_puerto_malformado() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "abc"  # presente, pero no es un entero válido
    entorno["POSTGRES_APP_USER"] = "proptech_app"
    entorno["POSTGRES_APP_PASSWORD"] = "proptech_app"
    entorno["POSTGRES_DB"] = "proptech"

    resultado = subprocess.run(
        [sys.executable, "-c", "from proptech_api.app import crear_app; crear_app()"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, "el proceso debería terminar con POSTGRES_PORT inválido"
    assert "POSTGRES_PORT" in resultado.stderr, (
        "el error no nombra la variable rota: el mensaje es genérico "
        f"('Configuración inválida') y no dice que el problema es POSTGRES_PORT. "
        f"stderr={resultado.stderr!r}"
    )
