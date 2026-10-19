"""Configuración inicial o de una versión; validación pura de su coherencia."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    dia_segundo_vencimiento: int | None = Field(default=None, ge=1, le=28)
    recargo_segundo_vencimiento: Porcentaje | None = None

    @model_validator(mode="after")
    def coherente(self) -> ConfiguracionEdificio:
        if self.tasa_mensual.decimal > Decimal("10"):
            raise ValueError("tasa_mensual debe estar entre 0.00 y 10.00")
        if self.porcentaje_fondo.decimal > Decimal("100"):
            raise ValueError("porcentaje_fondo debe estar entre 0.00 y 100.00")
        segundo, recargo = self.dia_segundo_vencimiento, self.recargo_segundo_vencimiento
        if self.modalidad_de_vencimiento == "unico":
            valido = segundo is None and recargo is None
        else:
            valido = (
                segundo is not None
                and segundo > self.dia_de_vencimiento
                and recargo is not None
                and Decimal("0.01") <= recargo.decimal <= Decimal("20.00")
            )
        if not valido:
            raise ValueError("vencimiento incoherente: revisar modalidad, segundo día y recargo")
        return self

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
