"""Clerk local: claves efímeras y API real como proptech_app, sin red externa."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from proptech_api.acceso import identidad_actual

from ._api_edificios import ApiEdificio


@pytest.fixture
def clerk_falso(monkeypatch: pytest.MonkeyPatch) -> rsa.RSAPrivateKey:
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    publica = (
        clave.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    monkeypatch.setenv("CLERK_JWT_KEY", publica)
    monkeypatch.setenv("CLERK_EMISOR", "https://clerk.invalid")
    monkeypatch.setenv("CLERK_PARTES_AUTORIZADAS", "https://proptech.invalid")
    return clave


@pytest.fixture
def api_clerk(clerk_falso: rsa.RSAPrivateKey, api_edificio: ApiEdificio) -> Iterator[ApiEdificio]:
    api_edificio.app.dependency_overrides.pop(identidad_actual)
    api_edificio.filas(
        "UPDATE persona SET clerk_usuario_id = 'user_Prueba' WHERE id = %s RETURNING id",
        (api_edificio.personas["editar"],),
    )
    yield api_edificio


def token(clave: rsa.RSAPrivateKey, **cambios: Any) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    claims = {
        "sub": "user_Prueba",
        "email": "invitada@example.invalid",
        "email_verified": True,
        "iss": "https://clerk.invalid",
        "azp": "https://proptech.invalid",
        "iat": ahora,
        "nbf": ahora - 1,
        "exp": ahora + 3600,
    }
    claims.update(cambios)
    claims = {campo: valor for campo, valor in claims.items() if valor is not None}
    return jwt.encode(claims, clave, algorithm="RS256")


def encabezados(clave: rsa.RSAPrivateKey, **cambios: Any) -> dict[str, str]:
    return {"Authorization": "Bearer " + token(clave, **cambios)}
