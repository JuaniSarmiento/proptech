"""Verificación local del token de sesión (D1): firma, claims y reloj explícito."""

import re
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import jwt
from jwt.exceptions import InvalidSubjectError

_USUARIO = re.compile(r"user_[A-Za-z0-9]{1,64}", flags=re.ASCII)
_TOLERANCIA_S = 5


class MotivoTokenInvalido(StrEnum):
    FIRMA = "firma_invalida"
    ALGORITMO = "algoritmo_invalido"
    FORMATO = "token_invalido"
    CLAIMS = "claims_invalidos"
    EMISOR = "emisor_invalido"
    VENCIDO = "token_vencido"
    NO_VIGENTE = "token_no_vigente"
    TIEMPOS = "tiempos_invalidos"
    PARTE = "parte_no_autorizada"
    SUJETO = "sujeto_invalido"
    PENDIENTE = "sesion_pendiente"


class TokenInvalido(Exception):
    """Sólo expone un motivo fijo, nunca el token ni el mensaje de PyJWT."""

    def __init__(self, motivo: MotivoTokenInvalido) -> None:
        self.motivo = motivo
        super().__init__(motivo.value)


@dataclass(frozen=True, slots=True)
class TokenVerificado:
    sub: str
    email: str | None
    email_verificado: bool


def verificar_token_de_sesion(
    token: str,
    clave_publica: str,
    partes_autorizadas: Collection[str],
    emisor: str,
    ahora: datetime,
) -> TokenVerificado:
    """No consulta red, base, entorno ni reloj real. `ahora` es UTC del llamador."""
    try:
        claims = jwt.decode(
            token,
            clave_publica,
            algorithms=["RS256"],
            issuer=emisor,
            options={
                "require": ["exp", "nbf", "sub", "azp", "iat", "iss"],
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
            },
        )
    except jwt.InvalidSignatureError:
        raise TokenInvalido(MotivoTokenInvalido.FIRMA) from None
    except jwt.InvalidAlgorithmError:
        raise TokenInvalido(MotivoTokenInvalido.ALGORITMO) from None
    except jwt.MissingRequiredClaimError:
        raise TokenInvalido(MotivoTokenInvalido.CLAIMS) from None
    except jwt.InvalidIssuerError:
        raise TokenInvalido(MotivoTokenInvalido.EMISOR) from None
    except InvalidSubjectError:
        raise TokenInvalido(MotivoTokenInvalido.SUJETO) from None
    except jwt.PyJWTError:
        raise TokenInvalido(MotivoTokenInvalido.FORMATO) from None

    if any(type(claims[campo]) is not int for campo in ("exp", "nbf", "iat")):
        raise TokenInvalido(MotivoTokenInvalido.TIEMPOS)
    instante = ahora.timestamp()
    if instante >= claims["exp"] + _TOLERANCIA_S:
        raise TokenInvalido(MotivoTokenInvalido.VENCIDO)
    if instante < claims["nbf"] - _TOLERANCIA_S or claims["iat"] > instante + _TOLERANCIA_S:
        raise TokenInvalido(MotivoTokenInvalido.NO_VIGENTE)
    if not isinstance(claims["azp"], str) or claims["azp"] not in partes_autorizadas:
        raise TokenInvalido(MotivoTokenInvalido.PARTE)
    if not isinstance(claims["sub"], str) or not _USUARIO.fullmatch(claims["sub"]):
        raise TokenInvalido(MotivoTokenInvalido.SUJETO)
    if claims.get("sts") == "pending":
        raise TokenInvalido(MotivoTokenInvalido.PENDIENTE)
    email = claims.get("email")
    return TokenVerificado(
        sub=claims["sub"],
        email=email if isinstance(email, str) else None,
        email_verificado=claims.get("email_verified") is True,
    )
