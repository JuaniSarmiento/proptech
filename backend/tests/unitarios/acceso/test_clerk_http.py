"""D7 (2b, tarea 5.4): el adaptador HTTP de Clerk, contra un servidor falso
que valida el contrato real (L-027): método, `Authorization`,
`Content-Type` y la forma del cuerpo.

Escenarios de `gestion-de-usuarios`: Envío exitoso; Reintento tras una
caída; Rechazo definitivo; Revocar una invitación enviada; Entrega sin
token crudo. Lecciones: L-001, L-007, L-013, L-027.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import pytest
from pydantic import SecretStr

from proptech_core.acceso.adaptadores.clerk_http import (
    AdaptadorClerkHttp,
    ClerkNoDisponible,
    ClerkRechazoDefinitivo,
)

from ..._clerk_falso import CLAVE_DE_PRUEBA, ServidorClerkFalso

SOBRE = "sobre-cifrado-de-prueba-no-token-crudo"
EMAIL = "vecina@example.invalid"
REDIRECT_URL = f"https://proptech-test.invalid/invitacion/{SOBRE}"


def _adaptador(base_url: str, *, plazo_s: float = 1.0) -> AdaptadorClerkHttp:
    return AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=base_url, plazo_s=plazo_s)


async def _invitar(base_url: str, *, plazo_s: float = 1.0) -> str:
    return await _adaptador(base_url, plazo_s=plazo_s).invitar(
        email=EMAIL, redirect_url=REDIRECT_URL, expires_in_days=7
    )


@pytest.mark.anyio
async def test_invitar_exitoso_manda_el_contrato_completo_y_devuelve_el_id() -> None:
    with ServidorClerkFalso(lambda *_: (201, {"id": "inv_abc123"})) as servidor:
        id_ = await _invitar(servidor.base_url)
    assert id_ == "inv_abc123"
    assert len(servidor.pedidos) == 1
    pedido = servidor.pedidos[0]
    assert (pedido["metodo"], pedido["ruta"]) == ("POST", "/invitations")
    assert pedido["cabeceras"]["Authorization"] == f"Bearer {CLAVE_DE_PRUEBA}"
    assert pedido["cabeceras"]["Content-Type"] == "application/json"
    assert pedido["cuerpo"] == {
        "email_address": EMAIL,
        "redirect_url": REDIRECT_URL,
        "notify": True,
        "expires_in_days": 7,
        "ignore_existing": False,
    }


@pytest.mark.anyio
@pytest.mark.parametrize("estado", [429, 500, 503])
async def test_429_y_5xx_son_clerk_no_disponible(estado: int) -> None:
    with ServidorClerkFalso(lambda *_: (estado, {"errors": []})) as servidor:
        with pytest.raises(ClerkNoDisponible):
            await _invitar(servidor.base_url)


@pytest.mark.anyio
async def test_4xx_definitivo_no_es_clerk_no_disponible() -> None:
    cuerpo = {"errors": [{"message": "email_address inválido"}]}
    with ServidorClerkFalso(lambda *_: (422, cuerpo)) as servidor:
        with pytest.raises(ClerkRechazoDefinitivo):
            await _invitar(servidor.base_url)


@pytest.mark.anyio
async def test_clerk_que_no_responde_da_clerk_no_disponible_acotado() -> None:
    def _lento(*_: Any) -> tuple[int, dict[str, Any]]:
        time.sleep(0.5)
        return 201, {"id": "inv_tarde"}

    with ServidorClerkFalso(_lento) as servidor:
        inicio = time.monotonic()
        with pytest.raises(ClerkNoDisponible):
            await _invitar(servidor.base_url, plazo_s=0.1)
        assert time.monotonic() - inicio < 1.0


@pytest.mark.anyio
async def test_clerk_apagado_da_clerk_no_disponible() -> None:
    with ServidorClerkFalso(lambda *_: (201, {"id": "inv_x"})) as servidor:
        base_url = servidor.base_url
    # El `with` ya cerró el socket: nadie escucha en ese puerto.
    with pytest.raises(ClerkNoDisponible):
        await _invitar(base_url, plazo_s=1.0)


@pytest.mark.anyio
async def test_revocar_llama_a_la_ruta_de_revoke_sin_cuerpo() -> None:
    with ServidorClerkFalso(lambda *_: (200, {})) as servidor:
        await _adaptador(servidor.base_url).revocar("inv_abc123")
    assert (servidor.pedidos[0]["metodo"], servidor.pedidos[0]["ruta"]) == (
        "POST",
        "/invitations/inv_abc123/revoke",
    )
    assert servidor.pedidos[0]["cuerpo"] is None


@pytest.mark.anyio
async def test_revocar_4xx_es_definitivo_5xx_es_no_disponible() -> None:
    with ServidorClerkFalso(lambda *_: (404, {})) as servidor:
        with pytest.raises(ClerkRechazoDefinitivo):
            await _adaptador(servidor.base_url).revocar("inv_x")
    with ServidorClerkFalso(lambda *_: (502, {})) as servidor:
        with pytest.raises(ClerkNoDisponible):
            await _adaptador(servidor.base_url).revocar("inv_x")


@pytest.mark.anyio
async def test_nada_del_cuerpo_ni_del_email_queda_en_los_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cuerpo = {"errors": [{"message": "email_address inválido"}]}
    with ServidorClerkFalso(lambda *_: (422, cuerpo)) as servidor:
        with caplog.at_level(logging.DEBUG), pytest.raises(ClerkRechazoDefinitivo):
            await _invitar(servidor.base_url)
    texto = "\n".join(
        registro.getMessage() + str(registro.__dict__.get("estado", ""))
        for registro in caplog.records
    )
    assert EMAIL not in texto and SOBRE not in texto and "email_address inválido" not in texto
