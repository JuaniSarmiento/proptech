"""Puertos del acceso: la aplicación no importa ARQ ni al worker."""

from typing import Any, Protocol

from proptech_core.compartido.cola import ResultadoEncolado


class ColaDeInvitaciones(Protocol):
    async def encolar(
        self, tarea: str, *, clave: str, request_id: str, **datos: Any
    ) -> ResultadoEncolado: ...
