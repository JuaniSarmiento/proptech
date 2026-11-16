"""Emitir lo revisado (E3, E7, E8): el pedido, las alertas aceptadas y la composición. Puro."""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_CLAVE_RAZONABLE = re.compile(r"[a-z_]{1,40}", re.ASCII)
_CLAVES = frozenset({"emision_id", "huella", "alertas_aceptadas", "vencimiento"})
_CLAVES_DE_VENCIMIENTO = frozenset({"fecha", "motivo"})
_MOTIVO_MAXIMO = 500
_SEIS_DECIMALES = Decimal("0.000001")


class PedidoInvalido(ValueError):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__(campo)


class ControlDuroActivo(Exception):
    def __init__(self, codigos: tuple[str, ...]) -> None:
        self.codigos = codigos
        super().__init__("control_duro")


class AlertasDistintas(Exception):
    pass


@dataclass(frozen=True)
class VencimientoCorrido:
    fecha: date
    motivo: str


@dataclass(frozen=True)
class PedidoDeEmision:
    emision_id: UUID
    huella: str
    alertas_aceptadas: tuple[str, ...]
    vencimiento: VencimientoCorrido | None


def _clave_ajena(clave: object, prefijo: str = "") -> str:
    """El nombre de un campo que no existe lo elige el cliente: sólo se nombra si es razonable."""
    if isinstance(clave, str) and _CLAVE_RAZONABLE.fullmatch(clave):
        return f"{prefijo}{clave}"
    return f"{prefijo}campo_no_permitido"


def _vencimiento(crudo: Any, periodo: date) -> VencimientoCorrido | None:
    if crudo is None:
        return None
    if not isinstance(crudo, Mapping):
        raise PedidoInvalido("vencimiento")
    for clave in crudo:
        if clave not in _CLAVES_DE_VENCIMIENTO:
            raise PedidoInvalido(_clave_ajena(clave, "vencimiento."))
    texto = crudo.get("fecha")
    try:
        if not isinstance(texto, str) or not _FECHA.fullmatch(texto):
            raise ValueError
        fecha = date.fromisoformat(texto)
    except ValueError:
        raise PedidoInvalido("vencimiento.fecha") from None
    if fecha < periodo:
        raise PedidoInvalido("vencimiento.fecha")
    motivo = crudo.get("motivo")
    if not isinstance(motivo, str) or not 1 <= len(motivo.strip()) <= _MOTIVO_MAXIMO:
        raise PedidoInvalido("vencimiento.motivo")
    return VencimientoCorrido(fecha, motivo.strip())


def pedido_de_emision(cuerpo: Mapping[str, Any], periodo: date) -> PedidoDeEmision:
    """El cuerpo de `POST .../emision`: `alertas_aceptadas` es obligatoria (puede ser `[]`);
    `vencimiento` es opcional y, si viene, lleva fecha (no anterior al período) y motivo
    (1 a 500)."""
    for clave in cuerpo:
        if clave not in _CLAVES:
            raise PedidoInvalido(_clave_ajena(clave))
    try:
        emision_id = UUID(str(cuerpo["emision_id"]))
    except KeyError, ValueError:
        raise PedidoInvalido("emision_id") from None
    huella = cuerpo.get("huella")
    if not isinstance(huella, str) or not huella:
        raise PedidoInvalido("huella")
    alertas = cuerpo.get("alertas_aceptadas")
    if not isinstance(alertas, list) or not all(isinstance(a, str) for a in alertas):
        raise PedidoInvalido("alertas_aceptadas")
    return PedidoDeEmision(
        emision_id, huella, tuple(alertas), _vencimiento(cuerpo.get("vencimiento"), periodo)
    )


def validar_alertas(
    controles: Sequence[Mapping[str, Any]], aceptadas: Sequence[str]
) -> tuple[str, ...]:
    """E7: un duro activo frena siempre (aunque venga aceptado); lo aceptado tiene que ser
    exactamente el conjunto de bloqueantes activos, ni más ni menos y sin repetir; una advertencia
    nunca se acepta. Devuelve los códigos aceptados, en el orden de los controles."""
    duros = tuple(str(c["codigo"]) for c in controles if c["nivel"] == "duro")
    if duros:
        raise ControlDuroActivo(duros)
    bloqueantes = tuple(str(c["codigo"]) for c in controles if c["nivel"] == "bloqueante")
    if Counter(aceptadas) != Counter(bloqueantes):
        raise AlertasDistintas
    return bloqueantes


def coeficientes_efectivos(pesos: Mapping[UUID, Decimal]) -> dict[UUID, str]:
    """El coeficiente efectivo que usó el reparto de un grupo: el peso de cada unidad sobre la
    suma de los pesos del grupo, con seis decimales, medio hacia arriba."""
    suma = sum(pesos.values(), Decimal(0))
    return {
        unidad: str((peso / suma).quantize(_SEIS_DECIMALES, rounding=ROUND_HALF_UP))
        for unidad, peso in pesos.items()
    }
