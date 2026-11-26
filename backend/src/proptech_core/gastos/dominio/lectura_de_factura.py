"""Lo que propone la IA para el borrador de una factura y el control de importe atípico (R12, R23,
H-037, D-169).

Dominio puro. La propuesta viene de un modelo y no es confiable: es un objeto con las cinco claves
`concepto`, `periodo`, `categoria_id`, `grupo_id` e `importe` (los valores pueden ser `null`); si no
lo es, `FueraDeContrato` y no se aplica nada. Si cumple el contrato, cada campo se valida solo: el
que no sirve queda sin valor y se anota con su motivo (`invalido`, o `fuera_del_vocabulario` para
una categoría o un grupo que el edificio no ofrece). Sólo se evalúan los campos que el gasto
todavía no tiene (`completar`): lo que cargó una persona o trajo el QR no se pisa ni se anota. El
texto del concepto es un dato, nunca una orden.

R23: un importe es atípico si es estrictamente mayor que el doble o estrictamente menor que la mitad
del promedio (media aritmética) de los gastos aprobados del proveedor en los 6 períodos anteriores,
con al menos uno. La comparación es exacta (sin redondear el promedio); el promedio que se muestra
se redondea medio hacia arriba.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.texto import recortado_sin_control

CAMPOS_DE_LA_PROPUESTA = ("concepto", "periodo", "categoria_id", "grupo_id", "importe")
#: R23: los períodos anteriores al del gasto que entran en el promedio.
VENTANA_EN_PERIODOS = 6

MOTIVO_INVALIDO = "invalido"
MOTIVO_FUERA_DEL_VOCABULARIO = "fuera_del_vocabulario"

_PERIODO = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])", re.ASCII)
#: `NUMERIC(14,2)`: hasta 12 dígitos enteros.
_IMPORTE = re.compile(r"[0-9]{1,12}\.[0-9]{2}", re.ASCII)
_CONCEPTO_MAXIMO = 200
_CENTAVO = Decimal("0.01")


class FueraDeContrato(Exception):
    """La respuesta del modelo no es un objeto con las cinco claves."""


class _Invalido(Exception):
    def __init__(self, motivo: str = MOTIVO_INVALIDO) -> None:
        self.motivo = motivo
        super().__init__(motivo)


@dataclass(frozen=True)
class PropuestaValidada:
    concepto: str | None = None
    periodo: date | None = None
    categoria_id: UUID | None = None
    grupo_id: UUID | None = None
    importe: Dinero | None = None
    #: `{campo: motivo}` de lo que se evaluó y no sirvió.
    descartados: dict[str, str] = field(default_factory=dict)


def _concepto(valor: Any) -> str:
    if not isinstance(valor, str) or len(valor) > _CONCEPTO_MAXIMO:
        raise _Invalido
    try:
        recortado = recortado_sin_control(valor)
    except ValueError:
        raise _Invalido from None
    if not recortado:
        raise _Invalido
    return recortado


def _periodo(valor: Any) -> date:
    encontrado = _PERIODO.fullmatch(valor) if isinstance(valor, str) else None
    if encontrado is None:
        raise _Invalido
    try:
        return date(int(encontrado.group(1)), int(encontrado.group(2)), 1)
    except ValueError:
        raise _Invalido from None


def _importe(valor: Any) -> Dinero:
    if not isinstance(valor, str) or _IMPORTE.fullmatch(valor) is None:
        raise _Invalido
    dinero = Dinero(valor)
    if dinero.decimal <= 0:
        raise _Invalido
    return dinero


def _del_vocabulario(valor: Any, ofrecidos: Collection[UUID]) -> UUID:
    if not isinstance(valor, str):
        raise _Invalido
    try:
        elegido = UUID(valor)
    except ValueError:
        raise _Invalido(MOTIVO_FUERA_DEL_VOCABULARIO) from None
    if elegido not in ofrecidos:
        raise _Invalido(MOTIVO_FUERA_DEL_VOCABULARIO)
    return elegido


def validar_propuesta(
    propuesta: Any,
    *,
    categorias: Collection[UUID],
    grupos: Collection[UUID],
    completar: Collection[str],
) -> PropuestaValidada:
    """Valida cada campo de `completar` contra la propuesta. `categorias` y `grupos` son los ids
    activos del edificio del gasto. `FueraDeContrato` si no es un objeto con las cinco claves."""
    if not isinstance(propuesta, dict) or not all(c in propuesta for c in CAMPOS_DE_LA_PROPUESTA):
        raise FueraDeContrato
    validadores = {
        "concepto": _concepto,
        "periodo": _periodo,
        "categoria_id": lambda v: _del_vocabulario(v, categorias),
        "grupo_id": lambda v: _del_vocabulario(v, grupos),
        "importe": _importe,
    }
    validos: dict[str, Any] = {}
    descartados: dict[str, str] = {}
    for campo in CAMPOS_DE_LA_PROPUESTA:
        if campo not in completar:
            continue
        try:
            validos[campo] = validadores[campo](propuesta[campo])
        except _Invalido as invalido:
            descartados[campo] = invalido.motivo
    return PropuestaValidada(**validos, descartados=descartados)


@dataclass(frozen=True)
class ImporteAtipico:
    promedio: Dinero
    muestras: int


def evaluar_importe(importe: Dinero, historial: Sequence[Dinero]) -> ImporteAtipico | None:
    """R23: `None` si no hay historial o el importe está dentro de [mitad, doble] del promedio."""
    muestras = len(historial)
    if muestras == 0:
        return None
    suma = sum((h.decimal for h in historial), Decimal(0))
    # Exacto: importe > 2 * suma / n  y  importe < suma / (2 * n), sin dividir.
    cantidad = Decimal(muestras)
    mas_del_doble = importe.decimal * cantidad > 2 * suma
    menos_de_la_mitad = importe.decimal * cantidad * 2 < suma
    if not (mas_del_doble or menos_de_la_mitad):
        return None
    promedio = (suma / cantidad).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
    return ImporteAtipico(Dinero(f"{promedio:.2f}"), muestras)
