"""Enlaces firmados para descargar el PDF de la expensa (7, H-015, D-070, E13).

El PDF nunca tiene una dirección pública: se descarga con un token que firma el servidor con
HMAC-SHA256 y la clave `PROPTECH_CLAVE_DE_ENLACES`, sobre la administración, el documento, la
variante y el vencimiento. El token lleva sólo esos identificadores (nunca un dato personal) y
tiene la forma `<cuerpo en base64url>.<firma en hexadecimal minúscula>`.

La firma se compara como **texto** exacto y en tiempo constante, no decodificada: una firma en
hexadecimal con otras mayúsculas decodificaría igual, y una en base64 puede cambiar bits que no
cuentan; el texto exacto no deja ninguna de las dos.

La verificación separa dos fallos: firma mala o token mal formado (`EnlaceAlterado`, 403) y firma
buena con el tiempo cumplido (`EnlaceVencido`, 410).
"""

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from proptech_core.liquidacion.dominio.documento import VARIANTES

#: Largo mínimo de la clave (caracteres): la configuración la exige igual.
LARGO_MINIMO_DE_LA_CLAVE = 32
#: Un token legítimo mide unos 200 caracteres; más que esto no se procesa.
_LARGO_MAXIMO_DEL_TOKEN = 1024


class EnlaceAlterado(Exception):
    """El token no es uno que este servidor haya firmado."""


class EnlaceVencido(Exception):
    """El token es auténtico pero ya pasó su vencimiento."""


@dataclass(frozen=True)
class EnlaceVerificado:
    administracion_id: UUID
    documento_id: UUID
    variante: str
    vence_en: datetime


def _firma(cuerpo: str, clave: str) -> str:
    return hmac.new(clave.encode(), cuerpo.encode("ascii"), hashlib.sha256).hexdigest()


def firmar_enlace(
    *,
    administracion_id: UUID,
    documento_id: UUID,
    variante: str,
    vence_en: datetime,
    clave: str,
) -> str:
    if len(clave) < LARGO_MINIMO_DE_LA_CLAVE:
        raise ValueError("clave: demasiado corta")
    if vence_en.tzinfo is None:
        raise ValueError("vence_en: tiene que llevar zona horaria")
    datos = {
        "a": str(administracion_id),
        "d": str(documento_id),
        "v": variante,
        "e": int(vence_en.astimezone(UTC).timestamp()),
    }
    cuerpo = (
        base64.urlsafe_b64encode(json.dumps(datos, separators=(",", ":"), sort_keys=True).encode())
        .rstrip(b"=")
        .decode()
    )
    return f"{cuerpo}.{_firma(cuerpo, clave)}"


def verificar_enlace(token: str, *, clave: str, ahora: datetime) -> EnlaceVerificado:
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
        variante = datos["v"]
        if variante not in VARIANTES:
            raise EnlaceAlterado
        enlace = EnlaceVerificado(
            administracion_id=UUID(datos["a"]),
            documento_id=UUID(datos["d"]),
            variante=variante,
            vence_en=datetime.fromtimestamp(int(datos["e"]), UTC),
        )
    except binascii.Error, ValueError, KeyError, TypeError:
        raise EnlaceAlterado from None
    if ahora >= enlace.vence_en:
        raise EnlaceVencido
    return enlace
