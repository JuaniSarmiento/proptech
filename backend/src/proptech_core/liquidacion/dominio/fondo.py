"""Fondo de reserva (R13, R15): un porcentaje de la ordinaria prorrateada, sin cargos."""

from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.compartido.reparto import (
    ParteARepartir,
    clave_de_orden_natural,
    redondear_al_centavo,
    repartir,
)
from proptech_core.liquidacion.dominio.reparto import UnidadDelPadron

_CERO = Dinero("0.00")


def fondo_de_reserva(
    ordinarias: Mapping[UUID, Dinero],
    porcentaje: Porcentaje,
    unidades: Mapping[UUID, UnidadDelPadron],
) -> dict[UUID, Dinero]:
    """El total del fondo es `porcentaje` de la suma de las ordinarias, redondeado medio hacia
    arriba al centavo; se reparte en proporción a la ordinaria de cada unidad (mayor resto), así la
    suma da exacto el total (R07). Una ordinaria negativa no genera fondo."""
    base = sum((max(o.decimal, Decimal(0)) for o in ordinarias.values()), Decimal(0))
    total = redondear_al_centavo(base * porcentaje.decimal / Decimal(100))
    if total == _CERO or base == 0:
        return {unidad: _CERO for unidad in ordinarias}
    partes = [
        ParteARepartir(
            unidad,
            max(ordinaria.decimal, Decimal(0)),
            clave_de_orden_natural(unidades[unidad].identificador, unidad),
        )
        for unidad, ordinaria in ordinarias.items()
    ]
    return {UUID(str(k)): v for k, v in repartir(total, partes).items()}
