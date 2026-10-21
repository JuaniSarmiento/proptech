"""Puertos del acceso: la aplicación no importa ARQ, al worker ni a Clerk."""

from typing import Any, Protocol

from proptech_core.compartido.cola import ResultadoEncolado


class ColaDeInvitaciones(Protocol):
    async def encolar(
        self,
        tarea: str,
        *,
        clave: str,
        request_id: str,
        expira_en_s: int | None = None,
        **datos: Any,
    ) -> ResultadoEncolado: ...


class ClienteDeClerk(Protocol):
    """D7: el worker habla con Clerk a través de este puerto; el adaptador
    HTTP vive en `adaptadores/clerk_http.py`. Nunca transporta el sobre ni
    el token crudo: sólo `redirect_url`, que ya lleva el sobre cifrado."""

    async def invitar(self, *, email: str, redirect_url: str, expires_in_days: int) -> str:
        """Crea la invitación en Clerk y devuelve su id (`inv_...`)."""

    async def revocar(self, clerk_invitacion_id: str) -> None: ...
