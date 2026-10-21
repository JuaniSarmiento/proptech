"""D7: adaptador HTTP de Clerk (`ClienteDeClerk`, en `puertos.py`).

Nunca loguea el cuerpo de Clerk, el email ni el sobre: sólo el código de
estado y un motivo fijo (D7, L-007). `httpx` es dependencia directa del
backend (pyproject.toml), con un plazo propio de 10 s por llamada.
"""

from __future__ import annotations

import logging

import httpx
from pydantic import SecretStr

_logger = logging.getLogger("proptech_core.acceso.adaptadores.clerk_http")

#: Plazo por llamada (D7): ni más ni menos, para que un Clerk que no
#: responde no cuelgue el intento más allá de lo que el reintento espera.
PLAZO_CLERK_S = 10.0

#: Base de la API de Clerk (D7, *createInvitation*).
BASE_CLERK = "https://api.clerk.com/v1"


class ClerkNoDisponible(Exception):
    """429, 5xx o la llamada no responde/falla de red (D7): pasajero, el
    worker la reintenta."""


class ClerkRechazoDefinitivo(Exception):
    """Un 4xx que no es 429 (D7): no se reintenta, la invitación queda
    `fallida`."""


class AdaptadorClerkHttp:
    """Adaptador del puerto `ClienteDeClerk` (D7) sobre la API REST de
    Clerk. Un cliente nuevo por llamada: el worker no mantiene un pool de
    conexiones HTTP entre trabajos."""

    def __init__(
        self,
        clave_secreta: SecretStr,
        *,
        base_url: str = BASE_CLERK,
        plazo_s: float = PLAZO_CLERK_S,
    ) -> None:
        self._clave = clave_secreta
        self._base_url = base_url
        self._plazo_s = plazo_s

    def _cabeceras(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._clave.get_secret_value()}",
            "Content-Type": "application/json",
        }

    async def _pedido(
        self, metodo: str, ruta: str, *, cuerpo: dict[str, object] | None
    ) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=self._plazo_s) as cliente:
                respuesta = await cliente.request(
                    metodo, f"{self._base_url}{ruta}", headers=self._cabeceras(), json=cuerpo
                )
        except httpx.TimeoutException, httpx.TransportError:
            _logger.warning("clerk_no_disponible", extra={"motivo": "sin_respuesta"})
            raise ClerkNoDisponible("clerk no disponible") from None
        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            _logger.warning("clerk_no_disponible", extra={"estado": respuesta.status_code})
            raise ClerkNoDisponible("clerk no disponible") from None
        if respuesta.status_code >= 400:
            _logger.warning("clerk_rechazo_definitivo", extra={"estado": respuesta.status_code})
            raise ClerkRechazoDefinitivo("clerk rechazó el pedido") from None
        if not respuesta.content:
            return {}
        datos = respuesta.json()
        return datos if isinstance(datos, dict) else {}

    async def invitar(self, *, email: str, redirect_url: str, expires_in_days: int) -> str:
        datos = await self._pedido(
            "POST",
            "/invitations",
            cuerpo={
                "email_address": email,
                "redirect_url": redirect_url,
                "notify": True,
                "expires_in_days": expires_in_days,
                "ignore_existing": False,
            },
        )
        return str(datos.get("id"))

    async def revocar(self, clerk_invitacion_id: str) -> None:
        await self._pedido("POST", f"/invitations/{clerk_invitacion_id}/revoke", cuerpo=None)
