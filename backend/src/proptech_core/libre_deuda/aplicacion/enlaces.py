"""El enlace firmado del PDF de un certificado de libre deuda (H-041, D-070).

La firma es la compartida de `proptech_core.compartido.enlaces`, con el tipo `libre_deuda` dentro
de lo firmado: un token de expensa o de comprobante no baja un certificado ni al revés. El token
lleva sólo la administración, el certificado y el vencimiento (nunca un dato personal).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from proptech_core.compartido.enlaces import EnlaceAlterado, EnlaceVencido, firmar, verificar

__all__ = [
    "EnlaceAlterado",
    "EnlaceDelCertificado",
    "EnlaceVencido",
    "firmar_enlace",
    "verificar_enlace",
]

TIPO = "libre_deuda"


@dataclass(frozen=True)
class EnlaceDelCertificado:
    administracion_id: UUID
    certificado_id: UUID


def firmar_enlace(
    *, administracion_id: UUID, certificado_id: UUID, vence_en: datetime, clave: str
) -> str:
    return firmar(
        TIPO,
        {"a": str(administracion_id), "i": str(certificado_id)},
        vence_en=vence_en,
        clave=clave,
    )


def verificar_enlace(token: str, *, clave: str, ahora: datetime) -> EnlaceDelCertificado:
    """`EnlaceAlterado` (403) o `EnlaceVencido` (410)."""
    datos = verificar(token, tipo=TIPO, clave=clave, ahora=ahora)
    try:
        return EnlaceDelCertificado(UUID(datos["a"]), UUID(datos["i"]))
    except ValueError, KeyError, TypeError:
        raise EnlaceAlterado from None
