"""La propuesta de la IA, validada campo por campo (H-019, E5, D-164).

Lo que dice la imagen es un dato no confiable: cada campo que no cumple su formato vuelve `None`, y
nada de lo que pase por acá crea un pago. Las claves de más se ignoran.
"""

import re
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal

PROPUESTA_VACIA: dict[str, str | None] = {
    "banco": None,
    "numero_de_operacion": None,
    "fecha": None,
    "monto": None,
    "cbu_origen": None,
}

_LARGO_MAXIMO = 100
_DIAS_HACIA_ATRAS = 365
_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MONTO = re.compile(r"[0-9]+\.[0-9]{2}")
_CBU = re.compile(r"[0-9]{22}")


def _texto(valor: object) -> str | None:
    if not isinstance(valor, str):
        return None
    recortado = valor.strip()
    return recortado if 0 < len(recortado) <= _LARGO_MAXIMO else None


def _fecha(valor: object, hoy: date) -> str | None:
    if not isinstance(valor, str) or not _FECHA.fullmatch(valor):
        return None
    try:
        fecha = date.fromisoformat(valor)
    except ValueError:
        return None
    return valor if hoy - timedelta(days=_DIAS_HACIA_ATRAS) <= fecha <= hoy else None


def _monto(valor: object) -> str | None:
    if not isinstance(valor, str) or not _MONTO.fullmatch(valor):
        return None
    return valor if Decimal(valor) > 0 else None


def _cbu(valor: object) -> str | None:
    return valor if isinstance(valor, str) and _CBU.fullmatch(valor) else None


def validar_propuesta(cruda: Mapping[str, object], hoy: date) -> dict[str, str | None]:
    """Las cinco claves, con `None` en lo que no cumple (o si `cruda` no es un objeto)."""
    if not isinstance(cruda, Mapping):
        return dict(PROPUESTA_VACIA)
    return {
        "banco": _texto(cruda.get("banco")),
        "numero_de_operacion": _texto(cruda.get("numero_de_operacion")),
        "fecha": _fecha(cruda.get("fecha"), hoy),
        "monto": _monto(cruda.get("monto")),
        "cbu_origen": _cbu(cruda.get("cbu_origen")),
    }
