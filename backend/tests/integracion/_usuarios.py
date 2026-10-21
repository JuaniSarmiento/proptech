"""Dobles de entrega: nunca llaman a Clerk ni a servicios externos."""

import base64
import secrets
from typing import Any

import pytest

from proptech_core.compartido.cola import ResultadoEncolado

from ._api_edificios import ApiEdificio


class ColaFalsa:
    def __init__(self) -> None:
        self.trabajos: list[dict[str, Any]] = []

    async def encolar(
        self, tarea: str, *, clave: str, request_id: str, **datos: Any
    ) -> ResultadoEncolado:
        self.trabajos.append({"tarea": tarea, "clave": clave, "request_id": request_id, **datos})
        return ResultadoEncolado.ENCOLADO


def preparar(api: ApiEdificio, monkeypatch: pytest.MonkeyPatch) -> ColaFalsa:
    from proptech_core.compartido.configuracion import Configuracion

    monkeypatch.setenv(
        "INVITACIONES_CLAVE_CIFRADO", base64.b64encode(secrets.token_bytes(32)).decode()
    )
    api.app.state.configuracion = Configuracion()
    cola = ColaFalsa()
    api.app.state.cola = cola
    return cola
