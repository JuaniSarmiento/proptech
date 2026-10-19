"""Coeficiente e informe puro de R01, compartidos por padrón, grupos y semilla."""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal
from functools import total_ordering
from typing import Any, Literal, TypedDict

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

_PATRON = re.compile(r"^\d(\.\d{1,6})?$", re.ASCII)
_TEXTO_PATRON = r"^\d(\.\d{1,6})?$"
_CERO = Decimal("0.000000")


class CoeficienteInvalido(ValueError):
    """El valor recibido no es un coeficiente válido."""


@total_ordering
class Coeficiente:
    """Coeficiente inmutable construido sólo desde texto, sin signo."""

    __slots__ = ("_decimal",)
    _decimal: Decimal

    def __init__(self, texto: str) -> None:
        if type(texto) is not str:
            raise CoeficienteInvalido(f"el coeficiente debe ser texto, no {type(texto).__name__}")
        if not _PATRON.fullmatch(texto):
            # Nunca el texto recibido (L-002): este tipo valida campos de
            # parametros.yaml, y el lector promete no repetir el contenido
            # del archivo en sus errores.
            raise CoeficienteInvalido(
                "formato de coeficiente inválido: se espera un entero de un dígito, "
                "sin signo, con hasta 6 decimales"
            )
        if not Decimal("0") < Decimal(texto) <= Decimal("1"):
            raise CoeficienteInvalido("el coeficiente debe ser mayor que cero y hasta uno")
        object.__setattr__(self, "_decimal", Decimal(texto).quantize(_CERO))

    def a_texto(self) -> str:
        return f"{self._decimal:.6f}"

    @property
    def decimal(self) -> Decimal:
        return self._decimal

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Coeficiente es inmutable")

    def __reduce__(self) -> tuple[type[Coeficiente], tuple[str]]:
        return (Coeficiente, (self.a_texto(),))

    def __copy__(self) -> Coeficiente:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Coeficiente:
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Coeficiente):
            return NotImplemented
        return self._decimal == other._decimal

    def __hash__(self) -> int:
        return hash(self._decimal)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Coeficiente):
            return NotImplemented
        return self._decimal < other._decimal

    def __repr__(self) -> str:
        return f'Coeficiente("{self.a_texto()}")'

    def __str__(self) -> str:
        return self.a_texto()

    @classmethod
    def _validar(cls, valor: Any) -> Coeficiente:
        if isinstance(valor, Coeficiente):
            return valor
        if type(valor) is str:
            return cls(valor)
        raise CoeficienteInvalido(f"se esperaba texto o Coeficiente, no {type(valor).__name__}")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validar,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda p: p.a_texto(),
                return_schema=core_schema.str_schema(pattern=_TEXTO_PATRON),
            ),
            json_schema_input_schema=core_schema.str_schema(pattern=_TEXTO_PATRON),
        )


class InformeCoeficientes(TypedDict):
    suma: str
    diferencia: str
    estado: Literal["ok", "advertencia", "fuera_de_tolerancia"]


def informar_coeficientes(coeficientes: Iterable[Coeficiente]) -> InformeCoeficientes:
    suma = Decimal("0.000000")
    for coeficiente in coeficientes:
        if not isinstance(coeficiente, Coeficiente):
            raise TypeError("se esperaba Coeficiente")
        suma += coeficiente.decimal
    diferencia = suma - Decimal("1")
    estado: Literal["ok", "advertencia", "fuera_de_tolerancia"] = "fuera_de_tolerancia"
    if diferencia == 0:
        estado = "ok"
    elif abs(diferencia) <= Decimal("0.0001"):
        estado = "advertencia"
    return {"suma": f"{suma:.6f}", "diferencia": f"{diferencia:.6f}", "estado": estado}
