"""Tipo Porcentaje (D13, cambio 3a, deuda del 1b con dueño 3): representación
de un porcentaje sobre Decimal, nunca float, con el mismo patrón ASCII y
`fullmatch` que `Dinero` (L-008).

Se construye sólo desde texto (`^\\d{1,3}(\\.\\d{1,2})?$`, hasta 2 decimales,
sin signo: un porcentaje nunca es negativo por formato). El rango permitido
(0 a 10 para la tasa, 0 a 100 para el fondo de reserva o el factor de un
estado, 0.01 a 20 para el recargo del segundo vencimiento) es decisión de
cada campo que lo usa, no de este tipo: `parametros.py` lo envuelve con su
propio chequeo de rango, igual que ya hace con `Dinero` para `Factor` y
`CargoFijo`.
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import total_ordering
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# re.ASCII: mismo problema que `dinero.py` (rompedor, cambio 1b vuelta 2) —
# `\d` sin ese flag matchea cualquier dígito Unicode de categoría Nd
# (arábigo-índico, de ancho completo, etc.), no sólo 0-9, y `Decimal()` los
# interpreta igual que a los ASCII.
# fullmatch, no match + `^...$`: sin `re.MULTILINE`, `$` matchea antes de un
# `\n` final del string, así que `.match()` aceptaba "3.00\n" (L-002).
# Sin signo: un porcentaje nunca es negativo por formato (ni siquiera "-0").
_PATRON = re.compile(r"^\d{1,3}(\.\d{1,2})?$", re.ASCII)
_TEXTO_PATRON = r"^\d{1,3}(\.\d{1,2})?$"
_CERO = Decimal("0.00")


class PorcentajeInvalido(ValueError):
    """El valor recibido no es un porcentaje válido."""


@total_ordering
class Porcentaje:
    """Porcentaje inmutable construido sólo desde texto, sin signo."""

    __slots__ = ("_decimal",)
    _decimal: Decimal

    def __init__(self, texto: str) -> None:
        if type(texto) is not str:
            raise PorcentajeInvalido(f"el porcentaje debe ser texto, no {type(texto).__name__}")
        if not _PATRON.fullmatch(texto):
            # Nunca el texto recibido (L-002): este tipo valida campos de
            # parametros.yaml, y el lector promete no repetir el contenido
            # del archivo en sus errores.
            raise PorcentajeInvalido(
                "formato de porcentaje inválido: se espera un entero de hasta 3 dígitos, "
                "sin signo, con hasta 2 decimales"
            )
        object.__setattr__(self, "_decimal", Decimal(texto).quantize(_CERO))

    def a_texto(self) -> str:
        return f"{self._decimal:.2f}"

    @property
    def decimal(self) -> Decimal:
        return self._decimal

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Porcentaje es inmutable")

    def __reduce__(self) -> tuple[type[Porcentaje], tuple[str]]:
        return (Porcentaje, (self.a_texto(),))

    def __copy__(self) -> Porcentaje:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Porcentaje:
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Porcentaje):
            return NotImplemented
        return self._decimal == other._decimal

    def __hash__(self) -> int:
        return hash(self._decimal)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Porcentaje):
            return NotImplemented
        return self._decimal < other._decimal

    def __repr__(self) -> str:
        return f'Porcentaje("{self.a_texto()}")'

    def __str__(self) -> str:
        return self.a_texto()

    @classmethod
    def _validar(cls, valor: Any) -> Porcentaje:
        if isinstance(valor, Porcentaje):
            return valor
        if type(valor) is str:
            return cls(valor)
        raise PorcentajeInvalido(f"se esperaba texto o Porcentaje, no {type(valor).__name__}")

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
