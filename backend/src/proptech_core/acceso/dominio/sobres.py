"""D6: tokens aleatorios y sobres autenticados AES-256-GCM, sin estado externo."""

import base64
import binascii
import hashlib
import secrets
from datetime import datetime

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr


class SobreInvalido(ValueError):
    def __init__(self) -> None:
        super().__init__("sobre inválido")


def _codificar(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def generar(clave: SecretStr, vence: datetime) -> tuple[bytes, str]:
    token = secrets.token_urlsafe(32)
    cabecera = b"\x01" + int(vence.timestamp()).to_bytes(8, "big")
    nonce = secrets.token_bytes(12)
    cifrado = AESGCM(base64.b64decode(clave.get_secret_value())).encrypt(
        nonce, token.encode(), cabecera
    )
    return hashlib.sha256(token.encode()).digest(), _codificar(cabecera + nonce + cifrado)


def abrir(clave: SecretStr, sobre: str, ahora: datetime) -> str:
    try:
        datos = base64.b64decode(sobre + "=" * (-len(sobre) % 4), altchars=b"-_", validate=True)
        if (
            _codificar(datos) != sobre
            or len(datos) < 38
            or datos[0] != 1
            or int.from_bytes(datos[1:9], "big") <= ahora.timestamp()
        ):
            raise SobreInvalido
        crudo = AESGCM(base64.b64decode(clave.get_secret_value())).decrypt(
            datos[9:21], datos[21:], datos[:9]
        )
        return crudo.decode("ascii")
    except ValueError, InvalidTag, binascii.Error, UnicodeError, OverflowError:
        raise SobreInvalido from None
