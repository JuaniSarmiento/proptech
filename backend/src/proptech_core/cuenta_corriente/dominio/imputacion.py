"""Orden de imputación de R04 y destinos fijos de D-086 (D6), sin base."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida


class Componente(StrEnum):
    INTERES = "interes"
    ORDINARIA = "ordinaria"
    FONDO_DE_RESERVA = "fondo_de_reserva"
    EXTRAORDINARIA = "extraordinaria"


#: E5 (provisorio hasta A-4, P60): la respuesta de Alberto cambia esta tupla y sus tests.
ORDEN_DE_IMPUTACION = (
    Componente.INTERES,
    Componente.ORDINARIA,
    Componente.FONDO_DE_RESERVA,
    Componente.EXTRAORDINARIA,
)


@dataclass(frozen=True)
class Deuda:
    obligacion_id: UUID
    componente: Componente
    periodo: date
    vencimiento: date
    residual: Dinero


@dataclass(frozen=True)
class Destino:
    obligacion_id: UUID
    componente: Componente


@dataclass(frozen=True)
class Imputacion:
    obligacion_id: UUID
    componente: Componente
    importe: Dinero


_CERO = Dinero("0.00")


def _clave(deuda: Deuda) -> tuple[date, int, date, UUID]:
    return (
        deuda.periodo,
        ORDEN_DE_IMPUTACION.index(deuda.componente),
        deuda.vencimiento,
        deuda.obligacion_id,
    )


def imputar(
    deudas: Iterable[Deuda], importe: Dinero, destino: Destino | None = None
) -> tuple[list[Imputacion], Dinero]:
    """R04 o destino fijo. Devuelve las imputaciones y el sobrante (crédito a favor).

    Con destino fijo, el pedido que excede su componente se rechaza entero (E16): nunca se
    registra una parte ni se desvía el resto a R04."""
    if not importe > _CERO:
        raise EntradaInvalida("importe")
    pendientes = [x for x in deudas if x.residual > _CERO]
    if destino is not None:
        pendientes = [
            x
            for x in pendientes
            if (x.obligacion_id, x.componente) == (destino.obligacion_id, destino.componente)
        ]
        capacidad = _CERO
        for x in pendientes:
            capacidad = capacidad + x.residual
        if importe > capacidad:
            raise EntradaInvalida("destino")
    imputaciones: list[Imputacion] = []
    resto = importe
    for x in sorted(pendientes, key=_clave):
        if not resto > _CERO:
            break
        parte = min(resto, x.residual)
        imputaciones.append(Imputacion(x.obligacion_id, x.componente, parte))
        resto = resto - parte
    return imputaciones, resto
