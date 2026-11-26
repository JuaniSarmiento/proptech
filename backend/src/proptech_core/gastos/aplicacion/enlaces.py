"""El enlace firmado de la factura de un gasto (H-036, D-169, D-070).

Misma firma compartida que el comprobante del 8 y el PDF del 7 (`proptech_core.compartido.enlaces`),
con el tipo `factura` dentro de lo firmado: un token de otro tipo no baja una factura ni al revés.
El token lleva sólo la administración, el gasto y el vencimiento.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from proptech_core.compartido.enlaces import EnlaceAlterado, firmar, verificar

__all__ = [
    "EnlaceAlterado",
    "EnlaceDeLaFactura",
    "firmar_enlace_de_la_factura",
    "verificar_enlace_de_la_factura",
]

TIPO = "factura"


@dataclass(frozen=True)
class EnlaceDeLaFactura:
    administracion_id: UUID
    gasto_id: UUID


def firmar_enlace_de_la_factura(
    *, administracion_id: UUID, gasto_id: UUID, vence_en: datetime, clave: str
) -> str:
    return firmar(
        TIPO, {"a": str(administracion_id), "g": str(gasto_id)}, vence_en=vence_en, clave=clave
    )


def verificar_enlace_de_la_factura(token: str, *, clave: str, ahora: datetime) -> EnlaceDeLaFactura:
    """`EnlaceAlterado` (403) o `EnlaceVencido` (410, de la firma compartida)."""
    datos = verificar(token, tipo=TIPO, clave=clave, ahora=ahora)
    try:
        return EnlaceDeLaFactura(UUID(datos["a"]), UUID(datos["g"]))
    except ValueError, KeyError, TypeError:
        raise EnlaceAlterado from None
