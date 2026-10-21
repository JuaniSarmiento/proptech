"""D1: firmas locales, reloj inyectado y errores sin datos (L-007/008/013/019)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import socket
from datetime import UTC, datetime
from typing import Any

import jwt
import pytest

from proptech_core.acceso.dominio.token import TokenInvalido, verificar_token_de_sesion

EMISOR = "https://instancia-ficticia.clerk.accounts.dev"
ORIGEN = "https://proptech.example.test"
AHORA = 946684800  # Año 2000, independiente del reloj de la máquina.
MOTIVOS = {
    "firma_invalida",
    "algoritmo_invalido",
    "token_invalido",
    "claims_invalidos",
    "emisor_invalido",
    "token_vencido",
    "token_no_vigente",
    "tiempos_invalidos",
    "parte_no_autorizada",
    "sujeto_invalido",
    "sesion_pendiente",
}


@pytest.fixture(scope="module")
def claves() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        privada.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode(),
    )


@pytest.fixture
def claims() -> dict[str, Any]:
    return {
        "sub": "user_Prueba123",
        "iss": EMISOR,
        "azp": ORIGEN,
        "exp": AHORA + 60,
        "nbf": AHORA - 60,
        "iat": AHORA - 60,
        "email": "ficticio@example.test",
        "email_verified": True,
    }


def verificar(token: str, publica: str, ahora: int = AHORA) -> Any:
    return verificar_token_de_sesion(
        token, publica, (ORIGEN,), EMISOR, datetime.fromtimestamp(ahora, UTC)
    )


def rechazar(token: str, publica: str, motivo: str, ahora: int = AHORA) -> None:
    with pytest.raises(TokenInvalido) as error:
        verificar(token, publica, ahora)
    assert error.value.motivo == motivo
    assert error.value.motivo in MOTIVOS
    assert str(error.value) == motivo
    assert token not in str(error.value)


def test_valido_sin_red(
    claves: tuple[str, str], claims: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def red_prohibida(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("verificar un token no debe acceder a la red")

    monkeypatch.setattr(socket, "create_connection", red_prohibida)
    monkeypatch.setattr(socket.socket, "connect", red_prohibida)
    token = jwt.encode(claims, claves[0], algorithm="RS256")
    verificado = verificar(token, claves[1])
    assert verificado.sub == "user_Prueba123"
    assert verificado.email == "ficticio@example.test"
    assert verificado.email_verificado is True


def test_firma_con_otra_clave(claves: tuple[str, str], claims: dict[str, Any]) -> None:
    from cryptography.hazmat.primitives.asymmetric import rsa

    otra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rechazar(jwt.encode(claims, otra, algorithm="RS256"), claves[1], "firma_invalida")


def _base64url(datos: bytes) -> bytes:
    return base64.urlsafe_b64encode(datos).rstrip(b"=")


def token_hs256(claims: dict[str, Any], publica: str) -> str:
    # Construcción manual: el encoder de PyJWT ya rechaza PEM como secreto HMAC.
    cuerpo = b".".join(
        [
            _base64url(b'{"alg":"HS256","typ":"JWT"}'),
            _base64url(json.dumps(claims).encode()),
        ]
    )
    firma = hmac.new(publica.encode(), cuerpo, hashlib.sha256).digest()
    return (cuerpo + b"." + _base64url(firma)).decode()


def test_hs256_con_pem_publico(claves: tuple[str, str], claims: dict[str, Any]) -> None:
    rechazar(token_hs256(claims, claves[1]), claves[1], "algoritmo_invalido")


def test_none(claves: tuple[str, str], claims: dict[str, Any]) -> None:
    rechazar(jwt.encode(claims, "", algorithm="none"), claves[1], "algoritmo_invalido")


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("azp", "https://ajeno.example.test", "parte_no_autorizada"),
        ("azp", "AUSENTE", "claims_invalidos"),
        ("azp", [ORIGEN], "parte_no_autorizada"),
        ("iss", "AUSENTE", "claims_invalidos"),
        ("iss", "https://otra.clerk.accounts.dev", "emisor_invalido"),
        ("sub", "AUSENTE", "claims_invalidos"),
        ("sub", "otra_forma", "sujeto_invalido"),
        ("sub", "user_ñ", "sujeto_invalido"),
        ("sub", "user_\uff11\uff12", "sujeto_invalido"),
        ("sub", "user_x\n", "sujeto_invalido"),
        ("sub", " user_x", "sujeto_invalido"),
        ("sub", "user_x\t", "sujeto_invalido"),
        ("sub", "user_", "sujeto_invalido"),
        ("sub", "user_" + "x" * 65, "sujeto_invalido"),
        ("sub", 123, "sujeto_invalido"),
        ("sts", "pending", "sesion_pendiente"),
        ("exp", AHORA - 6, "token_vencido"),
        ("nbf", AHORA + 6, "token_no_vigente"),
        ("iat", AHORA + 6, "token_no_vigente"),
    ],
)
def test_claim_roto(
    claves: tuple[str, str], claims: dict[str, Any], campo: str, valor: Any, motivo: str
) -> None:
    if valor == "AUSENTE":
        claims.pop(campo)
    else:
        claims[campo] = valor
    rechazar(jwt.encode(claims, claves[0], algorithm="RS256"), claves[1], motivo)


@pytest.mark.parametrize("campo", ["exp", "nbf", "iat"])
@pytest.mark.parametrize("valor", ["AUSENTE", "946684800", True, False, None, 946684800.0])
def test_tiempos_son_enteros_requeridos(
    claves: tuple[str, str], claims: dict[str, Any], campo: str, valor: Any
) -> None:
    if valor == "AUSENTE":
        claims.pop(campo)
    else:
        claims[campo] = valor
    motivo = "claims_invalidos" if valor in ("AUSENTE", None) else "tiempos_invalidos"
    rechazar(jwt.encode(claims, claves[0], algorithm="RS256"), claves[1], motivo)


@pytest.mark.parametrize(
    ("campo", "desplazamiento", "valido"),
    [
        ("exp", -6, True),
        ("exp", -5, True),
        ("exp", 4, True),
        ("exp", 5, False),
        ("exp", 6, False),
        ("nbf", -6, False),
        ("nbf", -5, True),
        ("iat", -6, False),
        ("iat", -5, True),
    ],
)
def test_bordes_con_reloj_inyectado(
    claves: tuple[str, str],
    claims: dict[str, Any],
    campo: str,
    desplazamiento: int,
    valido: bool,
) -> None:
    claims.update(exp=AHORA + 120, nbf=AHORA - 120, iat=AHORA - 120)
    claims[campo] = AHORA
    ahora = AHORA + desplazamiento
    token = jwt.encode(claims, claves[0], algorithm="RS256")
    if valido:
        assert verificar(token, claves[1], ahora).sub == claims["sub"]
    else:
        motivo = "token_vencido" if campo == "exp" else "token_no_vigente"
        rechazar(token, claves[1], motivo, ahora)


@pytest.mark.parametrize("valor", ["AUSENTE", False, "true", "false", 1, None])
def test_email_solo_verificado_si_booleano_true(
    claves: tuple[str, str], claims: dict[str, Any], valor: Any
) -> None:
    if valor == "AUSENTE":
        claims.pop("email_verified")
    else:
        claims["email_verified"] = valor
    token = jwt.encode(claims, claves[0], algorithm="RS256")
    assert verificar(token, claves[1]).email_verificado is False


@pytest.mark.parametrize("valor", [None, 12, ["ficticio@example.test"]])
def test_email_opcional_sin_coercion(
    claves: tuple[str, str], claims: dict[str, Any], valor: Any
) -> None:
    claims["email"] = valor
    token = jwt.encode(claims, claves[0], algorithm="RS256")
    assert verificar(token, claves[1]).email is None


def test_no_es_jwt(claves: tuple[str, str]) -> None:
    rechazar("dato-marcado-que-no-es-jwt", claves[1], "token_invalido")
