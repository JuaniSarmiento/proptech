"""Reglas puras del cambio de titular (R32, D-168)."""

from collections.abc import Collection, Sequence
from datetime import date
from uuid import UUID


class CambioInvalido(ValueError):
    """El pedido no es un cambio de titular válido. `campo` nombra qué falló, nunca el valor."""

    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__(campo)


def validar_pedido(
    *,
    fecha: date,
    hoy: date,
    vendedores: Sequence[UUID],
    cantidad_de_compradores: int,
    propietarios: Collection[UUID],
) -> None:
    """Lo que se sabe antes de resolver a los compradores: fecha no futura, vendedores y compradores
    presentes, sin vendedor repetido y todos propietarios actuales de la unidad."""
    if fecha > hoy:
        raise CambioInvalido("fecha")
    if not vendedores or len(set(vendedores)) != len(vendedores):
        raise CambioInvalido("vendedores")
    if not set(vendedores) <= set(propietarios):
        raise CambioInvalido("vendedores")
    if cantidad_de_compradores < 1:
        raise CambioInvalido("compradores")


def validar_compradores(
    *,
    vendedores: Sequence[UUID],
    compradores: Sequence[UUID],
    con_vinculo_en_la_unidad: Collection[UUID],
) -> None:
    """Con los compradores ya resueltos a persona: nadie compra dos veces ni se vende a sí mismo, y
    nadie que ya tenga otra asignación sobre la unidad (el otro copropietario o el inquilino): la
    base admite una sola por persona y unidad, y los inquilinos no se tocan."""
    if len(set(compradores)) != len(compradores):
        raise CambioInvalido("compradores")
    if set(compradores) & set(vendedores) or set(compradores) & set(con_vinculo_en_la_unidad):
        raise CambioInvalido("compradores")
