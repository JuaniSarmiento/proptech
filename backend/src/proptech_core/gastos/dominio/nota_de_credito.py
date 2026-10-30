"""La nota de crédito de un proveedor (R22, D-061, D-082)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from proptech_core.compartido.dinero import Dinero

_CERO = Dinero("0.00")


class DatosNotaDeCredito(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    importe: Dinero
    periodo: date
    cuit_emisor: str
    punto_de_venta: str
    tipo_de_comprobante: str
    numero_de_comprobante: str

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
