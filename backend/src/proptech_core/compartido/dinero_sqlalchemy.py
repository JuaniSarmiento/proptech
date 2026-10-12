"""Adaptador de SQLAlchemy para Dinero (D5): NUMERIC(14,2), sin aritmética."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Numeric
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from proptech_core.compartido.dinero import Dinero, MontoInvalido


class TipoDinero(TypeDecorator[Dinero]):
    """Columna NUMERIC(14,2) que sólo acepta/devuelve `Dinero`."""

    impl = Numeric(14, 2, asdecimal=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        if not isinstance(value, Dinero):
            raise MontoInvalido(f"se esperaba Dinero para esta columna, no {type(value).__name__}")
        return value.decimal

    def process_result_value(self, value: Any, dialect: Dialect) -> Dinero | None:
        if value is None:
            return None
        return Dinero.desde_decimal(value)
