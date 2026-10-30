"""Proveedores del edificio (R12, D-019): razón social + CUIT válido."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.gastos.dominio.cuit import FORMATO_CUIT, cuit_valido


class DatosProveedor(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    razon_social: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(recortado_sin_control)
    ]
    cuit: str

    @field_validator("cuit")
    @classmethod
    def cuit_valido_(cls, valor: str) -> str:
        if not cuit_valido(valor):
            raise ValueError(FORMATO_CUIT)
        return valor
