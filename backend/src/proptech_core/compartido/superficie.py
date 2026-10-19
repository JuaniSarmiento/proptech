"""Tipo Superficie (D13, cambio 3a, deuda del 1b con dueño 3): representación
de una superficie en m² sobre Decimal, nunca float, con el mismo patrón ASCII
y `fullmatch` que `Dinero` (L-008).

Se construye sólo desde texto (`^\\d{1,8}(\\.\\d{1,2})?$`, hasta 2 decimales,
sin signo: NUMERIC(10,2), la forma de `unidad.superficie_m2` de la tarea
3.1). Que sea estrictamente positiva (D2: `CHECK superficie_m2 > 0`) es
decisión de quien la usa, no de este tipo (igual que `Dinero` con
`Factor`/`CargoFijo` en `parametros.py`): `semilla.py` la envuelve con su
propio chequeo de positividad.
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import total_ordering
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# re.ASCII y fullmatch: misma familia de rompedores que `dinero.py`
# (dígitos Unicode no-ASCII, L-008; `\n` final, L-002). Sin signo: una
# superficie nunca es negativa por formato.
_PATRON = re.compile(r"^\d{1,8}(\.\d{1,2})?$", re.ASCII)
_TEXTO_PATRON = r"^\d{1,8}(\.\d{1,2})?$"
_CERO = Decimal("0.00")


class SuperficieInvalida(ValueError):
    """El valor recibido no es una superficie válida."""


@total_ordering
class Superficie:
    """Superficie inmutable, en m², construida sólo desde texto, sin signo."""

    __slots__ = ("_decimal",)
    _decimal: Decimal

    def __init__(self, texto: str) -> None:
        if type(texto) is not str:
            raise SuperficieInvalida(f"la superficie debe ser texto, no {type(texto).__name__}")
        if not _PATRON.fullmatch(texto):
            raise SuperficieInvalida(
                "formato de superficie inválido: se espera un entero de hasta 8 dígitos, "
                "sin signo, con hasta 2 decimales"
            )
        object.__setattr__(self, "_decimal", Decimal(texto).quantize(_CERO))

    def a_texto(self) -> str:
        return f"{self._decimal:.2f}"

    @property
    def decimal(self) -> Decimal:
        return self._decimal

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Superficie es inmutable")

    def __reduce__(self) -> tuple[type[Superficie], tuple[str]]:
        return (Superficie, (self.a_texto(),))

    def __copy__(self) -> Superficie:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Superficie:
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Superficie):
            return NotImplemented
        return self._decimal == other._decimal

    def __hash__(self) -> int:
        return hash(self._decimal)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Superficie):
            return NotImplemented
        return self._decimal < other._decimal

    def __repr__(self) -> str:
        return f'Superficie("{self.a_texto()}")'

    def __str__(self) -> str:
        return self.a_texto()

    @classmethod
    def _validar(cls, valor: Any) -> Superficie:
        if isinstance(valor, Superficie):
            return valor
        if type(valor) is str:
            return cls(valor)
        raise SuperficieInvalida(f"se esperaba texto o Superficie, no {type(valor).__name__}")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validar,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda s: s.a_texto(),
                return_schema=core_schema.str_schema(pattern=_TEXTO_PATRON),
            ),
            json_schema_input_schema=core_schema.str_schema(pattern=_TEXTO_PATRON),
        )
