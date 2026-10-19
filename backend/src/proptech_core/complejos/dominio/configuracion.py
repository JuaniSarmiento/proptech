"""Configuración inicial o de una versión; validación pura de su coherencia."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from proptech_core.compartido.parametros import Parametros
from proptech_core.compartido.porcentaje import Porcentaje


class ConfiguracionEdificio(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tasa_mensual: Porcentaje
    dias_de_gracia: int = Field(ge=0, le=31)
    forma_de_calculo: Literal["proporcional_por_dia", "mes_entero"]
    porcentaje_fondo: Porcentaje
    dia_de_vencimiento: int = Field(ge=1, le=28)
    modalidad_de_vencimiento: Literal["unico", "doble"]
    dia_segundo_vencimiento: int | None = Field(default=None, ge=1, le=28, validate_default=True)
    recargo_segundo_vencimiento: Porcentaje | None = Field(default=None, validate_default=True)

    @field_validator("tasa_mensual")
    @classmethod
    def tasa_en_rango(cls, valor: Porcentaje) -> Porcentaje:
        if valor.decimal > Decimal("10"):
            raise ValueError("tasa_mensual debe estar entre 0.00 y 10.00")
        return valor

    @field_validator("porcentaje_fondo")
    @classmethod
    def fondo_en_rango(cls, valor: Porcentaje) -> Porcentaje:
        if valor.decimal > Decimal("100"):
            raise ValueError("porcentaje_fondo debe estar entre 0.00 y 100.00")
        return valor

    @field_validator("dia_segundo_vencimiento")
    @classmethod
    def segundo_coherente(cls, valor: int | None, info: ValidationInfo) -> int | None:
        modalidad = info.data.get("modalidad_de_vencimiento")
        primero = info.data.get("dia_de_vencimiento")
        if modalidad == "unico" and valor is not None:
            raise ValueError("el vencimiento único no admite segundo día")
        if modalidad == "doble" and (valor is None or (primero is not None and valor <= primero)):
            raise ValueError("el segundo vencimiento debe ser posterior al primero")
        return valor

    @field_validator("recargo_segundo_vencimiento")
    @classmethod
    def recargo_coherente(cls, valor: Porcentaje | None, info: ValidationInfo) -> Porcentaje | None:
        modalidad = info.data.get("modalidad_de_vencimiento")
        if modalidad == "unico" and valor is not None:
            raise ValueError("el vencimiento único no admite recargo")
        if modalidad == "doble" and valor is None:
            raise ValueError("el vencimiento doble requiere recargo")
        if valor is not None and not Decimal("0.01") <= valor.decimal <= Decimal("20.00"):
            raise ValueError("recargo_segundo_vencimiento debe estar entre 0.01 y 20.00")
        return valor

    def validar_rango_recargo(self, parametros: Parametros) -> None:
        recargo = self.recargo_segundo_vencimiento
        rango = parametros.vencimiento.rango_recargo
        if recargo is not None and not rango.minimo <= recargo.decimal <= rango.maximo:
            raise ValueError("recargo_segundo_vencimiento fuera del rango de parámetros")

    @classmethod
    def desde_parametros(cls, parametros: Parametros) -> ConfiguracionEdificio:
        i, v = parametros.intereses, parametros.vencimiento
        return cls.model_validate(
            {
                "tasa_mensual": format(i.tasa_mensual, ".2f"),
                "dias_de_gracia": i.dias_de_gracia,
                "forma_de_calculo": i.forma_de_calculo,
                "porcentaje_fondo": format(parametros.fondo_de_reserva.porcentaje, ".2f"),
                "dia_de_vencimiento": v.dia,
                "modalidad_de_vencimiento": v.modalidad,
                "dia_segundo_vencimiento": v.dia_segundo_vencimiento,
                "recargo_segundo_vencimiento": (
                    None
                    if v.recargo_segundo_vencimiento is None
                    else format(v.recargo_segundo_vencimiento, ".2f")
                ),
            }
        )
