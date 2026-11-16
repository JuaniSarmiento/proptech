"""El ciclo de una liquidación emitida (E9, E10, P26, P39, D-157), sin base.

Una liquidación nace `emitida` y se cierra de una sola de dos maneras: `distribuida` (los vecinos ya
la recibieron; desde ahí no se anula) o `anulada` (con motivo, mientras no esté distribuida ni
tenga emitido el período siguiente). Nunca las dos: el evento es uno solo por emisión.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, MontoInvalido
from proptech_core.compartido.texto import recortado_sin_control

EMITIDA = "emitida"
DISTRIBUIDA = "distribuida"
ANULADA = "anulada"

#: `(campo, motivo)` del 409 que la ruta devuelve.
Conflicto = tuple[str, str]


def conflicto_al_distribuir(estado: str) -> Conflicto | None:
    """Sólo una emitida se distribuye: la ya distribuida y la anulada dan 409."""
    if estado == DISTRIBUIDA:
        return ("estado", "ya_distribuida")
    if estado == ANULADA:
        return ("estado", "anulada")
    return None


def conflicto_al_anular(estado: str, *, siguiente_emitido: bool) -> Conflicto | None:
    """Sólo una emitida se anula (el estado manda), y no con un período posterior emitido sin
    anular (P26): primero se anula el siguiente."""
    if estado == DISTRIBUIDA:
        return ("estado", "ya_distribuida")
    if estado == ANULADA:
        return ("estado", "anulada")
    if siguiente_emitido:
        return ("periodo", "periodo_siguiente_emitido")
    return None


def visible_para_el_consejo(estado: str) -> bool:
    """P39: el consejo no ve una liquidación emitida y no distribuida; una anulada nunca se
    distribuyó, así que tampoco."""
    return estado == DISTRIBUIDA


_CLAVE_RAZONABLE = re.compile(r"[a-z_]{1,40}", re.ASCII)
_MOTIVO_MAXIMO = 500
_COMPONENTES = ("ordinaria", "fondo_de_reserva", "extraordinaria")
_CLAVES_DE_ANULACION = frozenset({"motivo"})
_CLAVES_DE_CARGO = frozenset(
    {"operacion_id", "obligacion_origen_id", "importe", "componente", "motivo"}
)


class PedidoInvalido(ValueError):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__(campo)


@dataclass(frozen=True)
class PedidoDeCargo:
    operacion_id: UUID
    obligacion_origen_id: UUID
    importe: Dinero
    componente: str
    motivo: str


def _clave_ajena(clave: object) -> str:
    """El nombre de un campo que no existe lo elige el cliente: sólo se nombra si es razonable."""
    return (
        clave
        if isinstance(clave, str) and _CLAVE_RAZONABLE.fullmatch(clave)
        else "campo_no_permitido"
    )


def _solo_estas_claves(cuerpo: Mapping[str, Any], permitidas: frozenset[str]) -> None:
    for clave in cuerpo:
        if clave not in permitidas:
            raise PedidoInvalido(_clave_ajena(clave))


def _motivo(valor: object) -> str:
    if not isinstance(valor, str):
        raise PedidoInvalido("motivo")
    try:
        limpio = recortado_sin_control(valor)
    except ValueError:
        raise PedidoInvalido("motivo") from None
    if len(limpio) > _MOTIVO_MAXIMO:
        raise PedidoInvalido("motivo")
    return limpio


def _uuid(cuerpo: Mapping[str, Any], campo: str) -> UUID:
    try:
        valor = cuerpo[campo]
        if not isinstance(valor, str):
            raise ValueError
        return UUID(valor)
    except KeyError, ValueError:
        raise PedidoInvalido(campo) from None


def pedido_de_anulacion(cuerpo: Mapping[str, Any]) -> str:
    """El cuerpo de `POST .../anulacion`: sólo `motivo` (1 a 500, no en blanco). Devuelve el motivo
    recortado."""
    _solo_estas_claves(cuerpo, _CLAVES_DE_ANULACION)
    return _motivo(cuerpo.get("motivo"))


def pedido_de_cargo(cuerpo: Mapping[str, Any]) -> PedidoDeCargo:
    """El cuerpo de `POST .../cargos-cobrados-de-menos` (E11): exactamente sus cinco campos; el
    importe es texto (el signo y el cero los rechaza el libro, 422)."""
    _solo_estas_claves(cuerpo, _CLAVES_DE_CARGO)
    operacion_id = _uuid(cuerpo, "operacion_id")
    origen = _uuid(cuerpo, "obligacion_origen_id")
    try:
        importe = Dinero(cuerpo["importe"])
    except KeyError, MontoInvalido:
        raise PedidoInvalido("importe") from None
    componente = cuerpo.get("componente")
    if componente not in _COMPONENTES:
        raise PedidoInvalido("componente")
    return PedidoDeCargo(
        operacion_id, origen, importe, str(componente), _motivo(cuerpo.get("motivo"))
    )
