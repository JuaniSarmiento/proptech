"""`arranque_fallido` también ante un archivo de parámetros roto y una base inalcanzable (C2-8).

Escenarios de `entorno-de-ejecucion`: Archivo de parámetros mal formado; Base inalcanzable.
Se corre `crear_app()` en un subproceso (así el log sale por stdout como en el contenedor) sin
Docker: el YAML roto vive en `tmp_path` y la base "inalcanzable" es un puerto en el que nadie
escucha.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[3]
CONFIG = RAIZ / "config"

#: Marcador que no puede aparecer en ninguna línea del log (L-007).
CLAVE_MARCADOR = "clave-app-no-real-marcador-9d41e7"

_SCRIPT_ARRANQUE = (
    "from fastapi.testclient import TestClient\n"
    "from proptech_api.app import crear_app\n"
    "with TestClient(crear_app()):\n"
    "    pass\n"
)


def _puerto_cerrado() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return int(sonda.getsockname()[1])


def _arrancar(parametros: Path) -> subprocess.CompletedProcess[str]:
    entorno = dict(os.environ)
    entorno.update(
        {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": str(_puerto_cerrado()),
            "POSTGRES_DB": "proptech",
            "POSTGRES_APP_USER": "proptech_app",
            "POSTGRES_APP_PASSWORD": CLAVE_MARCADOR,
            "REDIS_HOST": "127.0.0.1",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "clave-redis-no-real",
            "PROPTECH_PARAMETROS": str(parametros),
        }
    )
    for variable in ("CLERK_JWT_KEY", "CLERK_SECRET_KEY", "INVITACIONES_CLAVE_CIFRADO"):
        entorno.pop(variable, None)
    return subprocess.run(
        [sys.executable, "-c", _SCRIPT_ARRANQUE],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _arranques_fallidos(salida: str) -> list[dict[str, Any]]:
    eventos = []
    for linea in salida.splitlines():
        try:
            evento = json.loads(linea)
        except ValueError:
            continue
        if isinstance(evento, dict) and evento.get("evento") == "arranque_fallido":
            eventos.append(evento)
    return eventos


def _sin_secretos(resultado: subprocess.CompletedProcess[str]) -> None:
    assert CLAVE_MARCADOR not in resultado.stdout
    assert CLAVE_MARCADOR not in resultado.stderr


def test_un_yaml_mal_formado_deja_arranque_fallido_con_el_archivo(tmp_path: Path) -> None:
    roto = tmp_path / "parametros.yaml"
    roto.write_text("version: [esto no cierra\n", encoding="utf-8")
    resultado = _arrancar(roto)
    assert resultado.returncode != 0
    fallidos = _arranques_fallidos(resultado.stdout)
    assert len(fallidos) == 1, resultado.stdout
    assert "parametros.yaml" in fallidos[0]["causa"]
    _sin_secretos(resultado)


def test_un_parametro_con_el_tipo_equivocado_deja_arranque_fallido_con_el_campo(
    tmp_path: Path,
) -> None:
    original = (CONFIG / "parametros.yaml").read_text(encoding="utf-8")
    equivocado = tmp_path / "parametros.yaml"
    equivocado.write_text(original.replace("dia: 10", "dia: no-es-un-numero"), encoding="utf-8")
    resultado = _arrancar(equivocado)
    assert resultado.returncode != 0
    fallidos = _arranques_fallidos(resultado.stdout)
    assert len(fallidos) == 1, resultado.stdout
    assert "dia" in fallidos[0]["causa"]
    _sin_secretos(resultado)


def test_una_base_inalcanzable_deja_arranque_fallido_sin_la_cadena_de_conexion() -> None:
    resultado = _arrancar(CONFIG / "parametros.yaml")
    assert resultado.returncode != 0
    fallidos = _arranques_fallidos(resultado.stdout)
    assert len(fallidos) == 1, resultado.stdout
    causa = fallidos[0]["causa"]
    assert "base de datos" in causa
    assert "alcanzable" in causa
    assert "postgresql://" not in causa
    _sin_secretos(resultado)
