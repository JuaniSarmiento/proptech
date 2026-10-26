"""Redondeo de montos sueltos y reparto exacto por mayor resto (D-113)."""

import re
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Any
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, MontoInvalido


def redondear_al_centavo(valor: Decimal) -> Dinero:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise MontoInvalido("el monto debe ser Decimal finito")
    with localcontext() as contexto:
        contexto.prec = 32
        return Dinero.desde_decimal(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def clave_de_orden_natural(identificador: str, id: UUID) -> tuple[Any, ...]:
    tramos = tuple(
        (0, int(t)) if re.fullmatch(r"[0-9]+", t) else (1, t.casefold())
        for t in re.findall(r"[0-9]+|[^0-9]+", identificador, flags=re.ASCII)
    )
    return tramos, identificador, id


class RepartoInvalido(ValueError):
    """Las partes o el total no cumplen el contrato de reparto."""


@dataclass(frozen=True)
class ParteARepartir:
    clave: Hashable
    peso: Decimal
    orden: tuple[Any, ...]


def repartir(total: Dinero, partes: Sequence[ParteARepartir]) -> dict[Hashable, Dinero]:
    if not isinstance(total, Dinero) or not partes:
        raise RepartoInvalido("se requiere un monto y al menos una parte")
    if len({p.clave for p in partes}) != len(partes):
        raise RepartoInvalido("las claves deben ser únicas")
    pesos = []
    for parte in partes:
        peso = parte.peso
        if not isinstance(peso, Decimal) or not peso.is_finite() or peso < 0:
            raise RepartoInvalido("el peso debe ser Decimal finito no negativo")
        exponente = peso.as_tuple().exponent
        if not isinstance(exponente, int) or exponente < -6 or peso.adjusted() >= 12:
            raise RepartoInvalido("el peso admite hasta 12 enteros y 6 decimales")
        numerador, denominador = peso.as_integer_ratio()
        pesos.append(numerador * 1_000_000 // denominador)
    suma_pesos = sum(pesos)
    if suma_pesos == 0:
        raise RepartoInvalido("la suma de pesos debe ser positiva")
    numerador, denominador = total.decimal.as_integer_ratio()
    centavos = abs(numerador) * 100 // denominador
    cocientes, restos = zip(*(divmod(centavos * peso, suma_pesos) for peso in pesos), strict=True)
    asignados = list(cocientes)
    faltan = centavos - sum(asignados)
    prioridad = sorted(range(len(partes)), key=lambda i: (-restos[i], partes[i].orden))
    for i in prioridad[:faltan]:
        asignados[i] += 1
    signo = "-" if numerador < 0 else ""
    return {
        parte.clave: Dinero(f"{signo}{cantidad // 100}.{cantidad % 100:02d}")
        for parte, cantidad in zip(partes, asignados, strict=True)
    }
