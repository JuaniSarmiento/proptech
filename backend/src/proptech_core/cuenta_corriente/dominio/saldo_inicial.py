"""Saldo inicial (R09, design D5 del 4c): el pedido, su validación, su firma y su agrupación. Puro."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from proptech_core.compartido.dinero import Dinero


@dataclass(frozen=True)
class OrigenDeCarga:
    tipo: str
    archivo: str | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class FilaDeDeuda:
    fila: int | None
    periodo: date
    vencimiento: date
    componente: str
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class FilaDeTotal:
    fila: int | None
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class FilaDeCredito:
    fila: int | None
    importe: Dinero


@dataclass(frozen=True)
class UnidadDeSaldoInicial:
    unidad_id: UUID
    modo: str
    filas: tuple[FilaDeDeuda | FilaDeTotal | FilaDeCredito, ...]


@dataclass(frozen=True)
class TotalesDeSaldoInicial:
    capital: Dinero
    interes_importado: Dinero
    credito: Dinero


@dataclass(frozen=True)
class PedidoNormalizado:
    complejo_id: UUID
    fecha_de_migracion: date
    origen: OrigenDeCarga
    unidades: tuple[UnidadDeSaldoInicial, ...]


def normalizar_pedido(
    *,
    complejo_id: UUID,
    fecha_de_migracion: date,
    origen: OrigenDeCarga,
    unidades: tuple[UnidadDeSaldoInicial, ...],
    hoy: date,
) -> PedidoNormalizado:
    return PedidoNormalizado(complejo_id, fecha_de_migracion, origen, unidades)


def firmar_pedido(pedido: PedidoNormalizado) -> str:
    return "v1:" + "0" * 64
