"""El cargo particular (R14, D-025): un importe contra una sola unidad,
que nunca se reparte entre las demás (D2 del design: tabla propia, sin
grupo de reparto — ni siquiera como columna nullable)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.texto import recortado_sin_control

_CERO = Dinero("0.00")


class DatosCargoParticular(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    unidad_id: UUID
    concepto: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(recortado_sin_control)
    ]
    importe: Dinero
    periodo: date
    motivo: Annotated[
        str, Field(min_length=1, max_length=500), AfterValidator(recortado_sin_control)
    ]

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
