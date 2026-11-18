"""La firma compartida de los enlaces de descarga (D-070, E13; 8, H-024, E1).

Un token tiene la forma `<cuerpo en base64url>.<firma en hexadecimal minúscula>`: HMAC-SHA256
con la clave `PROPTECH_CLAVE_DE_ENLACES` sobre un cuerpo JSON que lleva siempre el **tipo** del
enlace (`t`) y el vencimiento (`e`, segundos). El tipo va dentro de lo firmado: un token de
expensa no sirve para un comprobante ni al revés. Nunca lleva datos personales, sólo
identificadores.

La firma se compara como texto exacto y en tiempo constante. Se separan dos fallos: firma mala,
token mal formado o de otro tipo (`EnlaceAlterado`, 403) y firma buena con el tiempo cumplido
(`EnlaceVencido`, 410).
"""

import base64
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

#: Largo mínimo de la clave (caracteres): la configuración la exige igual.
LARGO_MINIMO_DE_LA_CLAVE = 32
#: Un token legítimo mide unos 200 caracteres; más que esto no se procesa.
_LARGO_MAXIMO_DEL_TOKEN = 1024


class EnlaceAlterado(Exception):
    """El token no es uno que este servidor haya firmado, o es de otro tipo."""


class EnlaceVencido(Exception):
    """El token es auténtico pero ya pasó su vencimiento."""


def _firma(cuerpo: str, clave: str) -> str:
    return hmac.new(clave.encode(), cuerpo.encode("ascii"), hashlib.sha256).hexdigest()


def firmar(tipo: str, datos: dict[str, str], *, vence_en: datetime, clave: str) -> str:
    if len(clave) < LARGO_MINIMO_DE_LA_CLAVE:
        raise ValueError("clave: demasiado corta")
    if vence_en.tzinfo is None:
        raise ValueError("vence_en: tiene que llevar zona horaria")
    cuerpo_de_datos: dict[str, Any] = {
        **datos,
        "t": tipo,
        "e": int(vence_en.astimezone(UTC).timestamp()),
    }
    cuerpo = (
        base64.urlsafe_b64encode(
            json.dumps(cuerpo_de_datos, separators=(",", ":"), sort_keys=True).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{cuerpo}.{_firma(cuerpo, clave)}"


def verificar(token: str, *, tipo: str, clave: str, ahora: datetime) -> dict[str, Any]:
    """Los datos firmados (con `t` y `e`) de un token del `tipo` dado y vigente."""
    if not isinstance(token, str) or not token.isascii() or len(token) > _LARGO_MAXIMO_DEL_TOKEN:
        raise EnlaceAlterado
    partes = token.split(".")
    if len(partes) != 2:
        raise EnlaceAlterado
    cuerpo, firma = partes
    if not hmac.compare_digest(_firma(cuerpo, clave), firma):
        raise EnlaceAlterado
    try:
        datos = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
        if not isinstance(datos, dict) or datos["t"] != tipo:
            raise EnlaceAlterado
        vence_en = datetime.fromtimestamp(int(datos["e"]), UTC)
    except binascii.Error, ValueError, KeyError, TypeError:
        raise EnlaceAlterado from None
    if ahora >= vence_en:
        raise EnlaceVencido
    return datos
