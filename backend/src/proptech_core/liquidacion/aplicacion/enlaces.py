"""Enlaces firmados para descargar el PDF de la expensa (7, H-015, D-070, E13).

El PDF nunca tiene una dirección pública: se descarga con un token que firma el servidor con
HMAC-SHA256 y la clave `PROPTECH_CLAVE_DE_ENLACES`, sobre la administración, el documento, la
variante y el vencimiento. El token lleva sólo esos identificadores (nunca un dato personal) y
tiene la forma `<cuerpo en base64url>.<firma en hexadecimal minúscula>`.

La firma y la verificación son las compartidas de `proptech_core.compartido.enlaces` (8, H-024),
con el tipo `expensa` dentro de lo firmado: un token de comprobante no baja una expensa. La
verificación separa dos fallos: firma mala, token mal formado o de otro tipo (`EnlaceAlterado`,
403) y firma buena con el tiempo cumplido (`EnlaceVencido`, 410).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from proptech_core.compartido.enlaces import (
    LARGO_MINIMO_DE_LA_CLAVE,
    EnlaceAlterado,
    EnlaceVencido,
    firmar,
    verificar,
)
from proptech_core.liquidacion.dominio.documento import VARIANTES

__all__ = [
    "LARGO_MINIMO_DE_LA_CLAVE",
    "EnlaceAlterado",
    "EnlaceVencido",
    "EnlaceVerificado",
    "firmar_enlace",
    "verificar_enlace",
]

TIPO = "expensa"


@dataclass(frozen=True)
class EnlaceVerificado:
    administracion_id: UUID
    documento_id: UUID
    variante: str
    vence_en: datetime


def firmar_enlace(
    *,
    administracion_id: UUID,
    documento_id: UUID,
    variante: str,
    vence_en: datetime,
    clave: str,
) -> str:
    return firmar(
        TIPO,
        {"a": str(administracion_id), "d": str(documento_id), "v": variante},
        vence_en=vence_en,
        clave=clave,
    )


def verificar_enlace(token: str, *, clave: str, ahora: datetime) -> EnlaceVerificado:
    datos = verificar(token, tipo=TIPO, clave=clave, ahora=ahora)
    try:
        variante = datos["v"]
        if variante not in VARIANTES:
            raise EnlaceAlterado
        return EnlaceVerificado(
            administracion_id=UUID(datos["a"]),
            documento_id=UUID(datos["d"]),
            variante=variante,
            vence_en=datetime.fromtimestamp(int(datos["e"]), UTC),
        )
    except (ValueError, KeyError, TypeError):
        raise EnlaceAlterado from None
