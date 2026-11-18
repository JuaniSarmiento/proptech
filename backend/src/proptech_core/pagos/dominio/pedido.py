"""El cuerpo de `POST .../pagos` (E2, E4, D-163), validado a mano y sin base.

El 422 informa el **primer** campo que falla, en el orden del contrato: `monto`, `partes`,
`fecha_de_transferencia`, `banco`, `numero_de_operacion`, `cbu_origen`; después que las partes sumen
el monto y no repitan unidad (`partes`). El comprobante y las unidades los decide la base.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, MontoInvalido, sumar
from proptech_core.compartido.texto import sin_caracteres_de_control
from proptech_core.pagos.dominio.normalizacion import normalizar

_MONTO = re.compile(r"[0-9]+\.[0-9]{2}", re.ASCII)
_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_CBU = re.compile(r"[0-9]{22}", re.ASCII)
_TEXTO_MAXIMO = 100
_DIAS_HACIA_ATRAS = 365


class PedidoInvalido(ValueError):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__(campo)


@dataclass(frozen=True)
class Parte:
    unidad_id: str
    importe: Dinero


@dataclass(frozen=True)
class PedidoDePago:
    #: Texto tal como vino: que exista y sea de quien lo informa lo decide la base.
    comprobante_id: str
    banco: str
    banco_normalizado: str
    numero_de_operacion: str
    numero_normalizado: str
    fecha_de_transferencia: date
    monto: Dinero
    cbu_origen: str | None
    partes: tuple[Parte, ...]


def _importe(valor: object, campo: str) -> Dinero:
    """Texto con dos decimales exactos y mayor que cero; un número JSON no es texto."""
    if not isinstance(valor, str) or not _MONTO.fullmatch(valor):
        raise PedidoInvalido(campo)
    try:
        importe = Dinero(valor)
    except MontoInvalido:
        raise PedidoInvalido(campo) from None
    if importe.decimal <= 0:
        raise PedidoInvalido(campo)
    return importe


def _parte(valor: object) -> Parte:
    if not isinstance(valor, Mapping):
        raise PedidoInvalido("partes")
    unidad = valor.get("unidad_id")
    try:
        if not isinstance(unidad, str):
            raise ValueError
        canonica = str(UUID(unidad))
    except ValueError:
        raise PedidoInvalido("partes") from None
    return Parte(canonica, _importe(valor.get("importe"), "partes"))


def _fecha(valor: object, hoy: date) -> date:
    if not isinstance(valor, str) or not _FECHA.fullmatch(valor):
        raise PedidoInvalido("fecha_de_transferencia")
    try:
        fecha = date.fromisoformat(valor)
    except ValueError:
        raise PedidoInvalido("fecha_de_transferencia") from None
    if fecha > hoy or fecha < hoy - timedelta(days=_DIAS_HACIA_ATRAS):
        raise PedidoInvalido("fecha_de_transferencia")
    return fecha


def _texto(valor: object, campo: str) -> tuple[str, str]:
    """Devuelve el texto tal como vino y su forma normalizada, que no puede quedar vacía."""
    if not isinstance(valor, str) or len(valor) > _TEXTO_MAXIMO:
        raise PedidoInvalido(campo)
    try:
        sin_caracteres_de_control(valor)
    except ValueError:
        raise PedidoInvalido(campo) from None
    normalizado = normalizar(valor)
    if not normalizado:
        raise PedidoInvalido(campo)
    return valor, normalizado


def _cbu(valor: object) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str) or not _CBU.fullmatch(valor):
        raise PedidoInvalido("cbu_origen")
    return valor


def pedido_de_pago(cuerpo: Any, hoy: date) -> PedidoDePago:
    if not isinstance(cuerpo, Mapping):
        raise PedidoInvalido("monto")
    monto = _importe(cuerpo.get("monto"), "monto")
    crudas = cuerpo.get("partes")
    if not isinstance(crudas, list) or not crudas:
        raise PedidoInvalido("partes")
    partes = tuple(_parte(p) for p in crudas)
    fecha = _fecha(cuerpo.get("fecha_de_transferencia"), hoy)
    banco, banco_normalizado = _texto(cuerpo.get("banco"), "banco")
    numero, numero_normalizado = _texto(cuerpo.get("numero_de_operacion"), "numero_de_operacion")
    cbu = _cbu(cuerpo.get("cbu_origen"))
    if len({p.unidad_id for p in partes}) != len(partes):
        raise PedidoInvalido("partes")
    if sumar(p.importe for p in partes) != monto:
        raise PedidoInvalido("partes")
    comprobante = cuerpo.get("comprobante_id")
    return PedidoDePago(
        comprobante if isinstance(comprobante, str) else "",
        banco,
        banco_normalizado,
        numero,
        numero_normalizado,
        fecha,
        monto,
        cbu,
        partes,
    )
