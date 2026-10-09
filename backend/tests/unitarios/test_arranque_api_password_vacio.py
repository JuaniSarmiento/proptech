"""Regresión: encontrado por el Rompedor (ronda 2), movido desde `tests/rompedor/`.

Mismo blindspot que rechazó el auditor, por otra puerta.

El motivo 2 (D11) se supone que evita que "falta configuración" se confunda
con "la base está caída". Pero un string vacío (`POSTGRES_PASSWORD=""`) no es
"falta" para pydantic: la variable de entorno EXISTE, sólo que vacía. Pydantic
no la marca `missing`, `Configuracion()` no explota, y la API arranca
tranquila con una contraseña vacía.

El error real recién va a aparecer en el primer /api/salud, como
`{"estado": "degradado", "base": "sin_conexion"}` — exactamente la confusión
"config rota disfrazada de base caída" que el motivo 2 dice haber resuelto.
Mismo mecanismo con POSTGRES_USER o POSTGRES_DB vacíos.
"""

import os
import subprocess
import sys


def test_el_proceso_no_debe_arrancar_con_password_vacio() -> None:
    entorno = dict(os.environ)
    entorno["POSTGRES_HOST"] = "db"
    entorno["POSTGRES_PORT"] = "5432"
    entorno["POSTGRES_USER"] = "proptech"
    entorno["POSTGRES_PASSWORD"] = ""  # presente, vacía: no es "falta" para pydantic
    entorno["POSTGRES_DB"] = "proptech"

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_api.app; print('ARRANCO')"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0, (
        "el proceso arrancó con POSTGRES_PASSWORD vacío en vez de terminar "
        f"nombrando el problema. stdout={resultado.stdout!r}"
    )
