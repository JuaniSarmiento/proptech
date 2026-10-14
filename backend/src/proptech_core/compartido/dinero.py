"""Tipo Dinero (D5): representación de montos sobre Decimal, nunca float.

Se construye sólo desde texto (`^-?\\d{1,12}(\\.\\d{1,2})?$`, 12 enteros = NUMERIC(14,2)),
se serializa siempre como texto con dos decimales y no tiene aritmética: el reparto
y las sumas son del cambio 4 (R07, D-046).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from functools import total_ordering
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

#   re.ASCII: `\d` sin ese flag matchea cualquier dígito Unicode de categoría
#   Nd (arábigo-índico, de ancho completo, etc.), no sólo 0-9, y `Decimal()`
#   los interpreta igual que a los ASCII (rompedor, cambio 1b vuelta 2).
#   fullmatch, no match + `^...$`: sin `re.MULTILINE`, `$` matchea antes de
#   un `\n` final del string, así que `.match()` aceptaba "1.00\n" (auditor,
#   cambio 1b vuelta 3; misma familia que L-002). `fullmatch` exige consumir
#   el string entero, así que ese `\n` sobrante lo rechaza.
_PATRON = re.compile(r"^-?\d{1,12}(\.\d{1,2})?$", re.ASCII)
_TEXTO_PATRON = r"^-?\d{1,12}(\.\d{1,2})?$"
_CERO = Decimal("0.00")


class MontoInvalido(ValueError):
    """El valor recibido no es un monto válido."""


@total_ordering
class Dinero:
    """Monto inmutable construido sólo desde texto."""

    __slots__ = ("_decimal",)
    _decimal: Decimal

    def __init__(self, texto: str) -> None:
        if type(texto) is not str:
            raise MontoInvalido(f"el monto debe ser texto, no {type(texto).__name__}")
        if not _PATRON.fullmatch(texto):
            # Nunca el texto recibido (D5, tarea 6.4): este mismo tipo valida
            # campos de parametros.yaml, y el lector promete no repetir el
            # contenido del archivo en sus errores (L-002).
            raise MontoInvalido(
                "formato de monto inválido: se espera un entero de hasta 12 dígitos, "
                "opcionalmente negativo, con hasta 2 decimales"
            )
        object.__setattr__(self, "_decimal", Decimal(texto).quantize(_CERO))

    @classmethod
    def desde_decimal(cls, valor: Decimal) -> Dinero:
        """Para adaptadores (SQLAlchemy, etc.): valida que sea finito, que
        tenga **a lo sumo dos decimales exactos** (rechaza, no redondea, si
        cuantizar a dos decimales cambiaría el valor) y que esté dentro del
        rango de NUMERIC(14,2).

        Antes (cambio 1b, vuelta 4) `quantize` redondeaba en silencio
        (`Decimal("12.345")` pasaba a `12.34` sin avisar) pese a que este
        docstring ya decía "valida", no "redondea"; y un valor que agotaba la
        precisión del contexto decimal (`Decimal("1e30")`) levantaba
        `decimal.InvalidOperation` sin atrapar en vez de `MontoInvalido`."""
        if not isinstance(valor, Decimal):
            raise MontoInvalido(f"se esperaba Decimal, no {type(valor).__name__}")
        if not valor.is_finite():
            raise MontoInvalido("el monto debe ser finito")
        try:
            cuantizado = valor.quantize(_CERO)
        except InvalidOperation:
            raise MontoInvalido("el monto está fuera de rango o tiene demasiados dígitos") from None
        if cuantizado != valor:
            raise MontoInvalido("el monto no puede tener más de dos decimales")
        return cls(str(cuantizado))

    def a_texto(self) -> str:
        valor = self._decimal
        if valor == 0:
            valor = _CERO
        texto = f"{valor:.2f}"
        if texto == "-0.00":
            texto = "0.00"
        return texto

    @property
    def decimal(self) -> Decimal:
        return self._decimal

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Dinero es inmutable")

    def __reduce__(self) -> tuple[type[Dinero], tuple[str]]:
        """Pickle (D16): reconstruye desde `a_texto()`, así la carga pasa de
        nuevo por la validación de `__init__` (L-008) en vez de asignar el
        estado interno con `setattr`, que `__setattr__` bloquea."""
        return (Dinero, (self.a_texto(),))

    def __copy__(self) -> Dinero:
        """Inmutable: una copia superficial es el mismo objeto (D16)."""
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Dinero:
        """Inmutable: una copia profunda también es el mismo objeto (D16)."""
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dinero):
            return NotImplemented
        return self._decimal == other._decimal

    def __hash__(self) -> int:
        return hash(self._decimal)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Dinero):
            return NotImplemented
        return self._decimal < other._decimal

    def __repr__(self) -> str:
        return f'Dinero("{self.a_texto()}")'

    def __str__(self) -> str:
        return self.a_texto()

    @classmethod
    def _validar(cls, valor: Any) -> Dinero:
        if isinstance(valor, Dinero):
            return valor
        if type(valor) is str:
            return cls(valor)
        raise MontoInvalido(f"se esperaba texto o Dinero, no {type(valor).__name__}")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validar,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda d: d.a_texto(),
                return_schema=core_schema.str_schema(pattern=_TEXTO_PATRON),
            ),
            json_schema_input_schema=core_schema.str_schema(pattern=_TEXTO_PATRON),
        )
