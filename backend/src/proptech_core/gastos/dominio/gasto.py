"""El gasto del edificio (R12, R13, R16, D-075)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.texto import recortado_sin_control

#: D3 (design.md): los cuatro campos de la clave de R12 viajan juntos o no
#: viajan; el orden es el de la clave (`cuit + punto de venta + tipo + número`).
CAMPOS_DE_FACTURA = (
    "cuit_emisor",
    "punto_de_venta",
    "tipo_de_comprobante",
    "numero_de_comprobante",
)

ESTADOS_DEL_GASTO = ("borrador", "sin_ia", "en_revision", "aprobado")
_CERO = Dinero("0.00")


class DatosGasto(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    concepto: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(recortado_sin_control)
    ]
    categoria_id: UUID
    grupo_id: UUID
    proveedor_id: UUID | None = None
    periodo: date
    tipo: Literal["ordinario", "extraordinario"] = "ordinario"
    importe: Dinero
    cuit_emisor: str | None = None
    punto_de_venta: str | None = None
    tipo_de_comprobante: str | None = None
    numero_de_comprobante: str | None = None
    #: Tarea 3.10: el documento del receptor que trae la factura (no es
    #: parte de la clave de duplicados de R12). Si no coincide con
    #: `complejo.cuit`, el caso de uso devuelve un aviso que no bloquea la
    #: carga. Texto libre (no todo receptor sin registrar tiene CUIT).
    documento_receptor: str | None = None

    @field_validator("periodo")
    @classmethod
    def periodo_primer_dia_del_mes(cls, valor: date) -> date:
        if valor.day != 1:
            raise ValueError("el período debe ser el primer día de un mes")
        return valor

    @field_validator("importe")
    @classmethod
    def importe_mayor_a_cero(cls, valor: Dinero) -> Dinero:
        if valor <= _CERO:
            raise ValueError("el importe debe ser mayor que cero")
        return valor

    @model_validator(mode="after")
    def factura_completa_o_ninguna(self) -> DatosGasto:
        presentes = {campo: getattr(self, campo) is not None for campo in CAMPOS_DE_FACTURA}
        if any(presentes.values()) and not all(presentes.values()):
            faltan = [campo for campo, ok in presentes.items() if not ok]
            raise ValueError(f"faltan los campos de la factura: {', '.join(faltan)}")
        return self
