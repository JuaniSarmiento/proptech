"""Ataque del rompedor (vuelta 2, F7; D7, L-007): `evento` es `record.msg`, y
eso sólo es una plantilla si quien loguea pasa una plantilla. Uvicorn, cuando
falla el lifespan, loguea en `uvicorn.error` el traceback ENTERO como `msg`
(Starlette se lo manda en `lifespan.startup.failed`, con `exc_text =
traceback.format_exc()`), con el mensaje de la excepción y las líneas de
código. `configurar_logs` recablea `uvicorn.error` y lo deja pasar tal cual.
"""

import subprocess
import sys
from pathlib import Path

MARCADOR = "marcador-lifespan-5c2a"


def test_falla_del_lifespan_no_deja_el_mensaje_de_la_excepcion(tmp_path: Path) -> None:
    (tmp_path / "app_que_falla.py").write_text(
        "from contextlib import asynccontextmanager\n"
        "from fastapi import FastAPI\n"
        "from proptech_core.compartido.logs import configurar_logs\n"
        "configurar_logs('api')\n"
        "@asynccontextmanager\n"
        "async def lifespan(app):\n"
        f"    raise RuntimeError('password authentication failed for user {MARCADOR}')\n"
        "    yield\n"
        "app = FastAPI(lifespan=lifespan)\n"
    )
    proceso = subprocess.run(
        [sys.executable, "-m", "uvicorn", "app_que_falla:app", "--port", "0", "--no-access-log"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    salida = proceso.stdout + proceso.stderr
    assert "uvicorn.error" in salida, "no se logueó la falla: el test no prueba nada"
    assert MARCADOR not in salida
    assert "raise RuntimeError" not in salida  # D7: nunca las líneas de código
