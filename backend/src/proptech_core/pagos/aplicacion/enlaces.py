"""El enlace firmado del comprobante de un pago (8, H-024, E11, D-070).

La firma es la compartida de `proptech_core.compartido.enlaces`, con el tipo `comprobante` dentro
de lo firmado: un token de expensa no baja un comprobante ni al revés. El token lleva sólo la
administración, el pago y el vencimiento (nunca un dato personal).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from proptech_core.compartido.enlaces import EnlaceAlterado, firmar, verificar

__all__ = [
    "EnlaceAlterado",
    "EnlaceDelComprobante",
    "firmar_enlace_del_comprobante",
    "verificar_enlace_del_comprobante",
]

TIPO = "comprobante"


@dataclass(frozen=True)
class EnlaceDelComprobante:
    administracion_id: UUID
    pago_id: UUID


def firmar_enlace_del_comprobante(
    *, administracion_id: UUID, pago_id: UUID, vence_en: datetime, clave: str
) -> str:
    return firmar(
        TIPO,
        {"a": str(administracion_id), "p": str(pago_id)},
        vence_en=vence_en,
        clave=clave,
    )


def verificar_enlace_del_comprobante(
    token: str, *, clave: str, ahora: datetime
) -> EnlaceDelComprobante:
    """`EnlaceAlterado` (403) o `EnlaceVencido` (410, de la firma compartida)."""
    datos = verificar(token, tipo=TIPO, clave=clave, ahora=ahora)
    try:
        return EnlaceDelComprobante(UUID(datos["a"]), UUID(datos["p"]))
    except ValueError, KeyError, TypeError:
        raise EnlaceAlterado from None
