"""Rompedor del cambio 2e `humo-y-ci`: el helper del log y la paridad del worker en el arranque.

R8/R9: `fugas_del_valor` + `capturar_todo` se presentan como "buscar un valor rechazado en TODO el
log", pero no ven una fuga seguida de un punto ni una que sale por un logger con
`propagate=False` (los que deja así `configurar_logs`: `arq`, `uvicorn`, `uvicorn.error`).
R10: la spec MODIFIED de `entorno-de-ejecucion` dice "la API **o el worker**"; la tarea 7.3 dejó la
pregunta sin verificar. Lo está: el worker no deja `arranque_fallido` ni con un `parametros.yaml`
roto ni con la base inalcanzable.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from proptech_core.compartido.logs import configurar_logs
from tests._registros_del_log import capturar_todo, fugas_del_valor

RAIZ = Path(__file__).resolve().parents[3]
CONFIG = RAIZ / "config"
CLAVE_MARCADOR = "clave-app-no-real-marcador-rompedor-5be1"


# --- R8: una fuga seguida de un punto ---------------------------------------------------------


def test_una_fuga_al_final_de_una_oracion_se_ve(caplog: pytest.LogCaptureFixture) -> None:
    """`(?![\\w.])` excluye el punto para no confundir `123` con `123.5`, pero así una fuga al
    final de una oración (`... no-es-uuid.`) es invisible."""
    with capturar_todo(caplog):
        logging.getLogger("proptech.algo").warning("administración rechazada: no-es-uuid.")
    assert fugas_del_valor(caplog.records, "no-es-uuid") != []


# --- R9: una fuga por un logger que no propaga ------------------------------------------------


def test_una_fuga_por_un_logger_que_no_propaga_se_ve(caplog: pytest.LogCaptureFixture) -> None:
    """`configurar_logs` deja `arq` con `propagate=False`; `caplog` cuelga de la raíz. Un worker
    que loguea el valor rechazado por `arq.jobs` (el logger real de ARQ) no deja rastro para el
    helper: el test del tenant pasaría con la fuga puesta."""
    arq = logging.getLogger("arq")
    estado = (list(arq.handlers), arq.propagate, arq.level)
    try:
        # Lo que `configurar_logs` le hace a `arq` (logs.py: handler propio y `propagate=False`),
        # sin tocar la raíz, donde vive el handler de `caplog`.
        arq.addHandler(logging.NullHandler())
        arq.propagate = False
        assert "arq" in configurar_logs.__doc__  # type: ignore[operator]
        with capturar_todo(caplog):
            logging.getLogger("arq.jobs").warning("tarea rechazada", extra={"valor": "no-es-uuid"})
        assert fugas_del_valor(caplog.records, "no-es-uuid") != []
    finally:
        arq.handlers[:] = estado[0]
        arq.propagate = estado[1]
        arq.setLevel(estado[2])


# --- R10: el worker sin `arranque_fallido` ----------------------------------------------------


def _puerto_cerrado() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return int(sonda.getsockname()[1])


def _arrancar_worker(parametros: Path, codigo: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-c", codigo],
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
