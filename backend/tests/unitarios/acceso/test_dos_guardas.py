"""4.4: rutas reales con solver y overrides; sin base, sin identidad completa."""

from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from proptech_api.acceso import identidad_actual, token_de_sesion_actual
from proptech_api.cuerpos import manejador_422
from proptech_core.acceso.dominio.token import TokenVerificado


@pytest.mark.parametrize(
    "cuerpo",
    [
        b'{"token":"sobre"}',
        b"",
        b"{",
        b"\xff",
        b"{}",
        b'{"token":5}',
        b'{"token":"sobre","extra":1}',
        b"[]",
    ],
)
@pytest.mark.parametrize("sesion_valida", [False, True])
def test_aceptar_autentica_antes_del_cuerpo_y_sin_persona(
    monkeypatch: pytest.MonkeyPatch, cuerpo: bytes, sesion_valida: bool
) -> None:
    from fastapi.exceptions import RequestValidationError

    from proptech_api import invitaciones
    from proptech_api.seguimiento import MiddlewareSeguimiento

    app = FastAPI()
    app.add_middleware(MiddlewareSeguimiento)
    app.include_router(invitaciones.router_de_token)
    app.add_exception_handler(RequestValidationError, manejador_422)
    llamadas: list[str] = []

    def token_contado() -> TokenVerificado:
        llamadas.append("token")
        if not sesion_valida:
            raise HTTPException(401)
        return TokenVerificado("user_SinVinculo", "invitada@example.invalid", True)

    def identidad_prohibida() -> None:
        raise AssertionError("esta ruta no resuelve persona completa")

    def aceptar_falso(*args: Any, **kwargs: Any) -> None:
        llamadas.append("aceptar")

    app.dependency_overrides[token_de_sesion_actual] = token_contado
    app.dependency_overrides[identidad_actual] = identidad_prohibida
    monkeypatch.setattr(invitaciones, "aceptar", aceptar_falso)
    app.state.fabrica_de_sesiones = object()
    app.state.configuracion = object()
    with TestClient(app, raise_server_exceptions=False) as cliente:
        r = cliente.post(
            "/api/invitaciones/aceptar",
            content=cuerpo,
            headers={"Content-Type": "application/json", "X-Proptech-Administracion": "no-uuid"},
        )
    esperado = 401 if not sesion_valida else (200 if cuerpo == b'{"token":"sobre"}' else 422)
    assert r.status_code == esperado, r.text
    assert llamadas == (["token", "aceptar"] if esperado == 200 else ["token"])


def test_sesion_sin_persona_llega_al_caso_de_uso(monkeypatch: pytest.MonkeyPatch) -> None:
    from proptech_api import sesion

    app = FastAPI()
    app.state.fabrica_de_sesiones = object()
    app.include_router(sesion.router_de_token)
    llamadas: list[str] = []

    def token() -> TokenVerificado:
        llamadas.append("token")
        return TokenVerificado("user_SinVinculo", None, False)

    def consultar(*args: Any) -> dict[str, Any]:
        llamadas.append("consultar")
        return {"persona": {"nombre": "Ficticia"}, "administraciones": []}

    app.dependency_overrides[token_de_sesion_actual] = token
    monkeypatch.setattr(sesion, "consultar", consultar)
    with TestClient(app) as cliente:
        r = cliente.get("/api/sesion")
    assert r.status_code == 200
    assert llamadas == ["token", "consultar"]
