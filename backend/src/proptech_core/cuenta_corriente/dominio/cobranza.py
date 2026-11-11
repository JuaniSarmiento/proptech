"""Situación de cobranza de una cuenta, sin base (R20, R30, D-109.4, D-143; design D6).

Se deriva cada vez del estado de la cuenta (D-074: nunca se guarda una marca de moroso).
"""

from dataclasses import dataclass
from datetime import date, timedelta

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.dominio.estado import EstadoDeCuenta
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

_CERO = Dinero("0.00")

SIN_DEUDA_VENCIDA = "sin_deuda_vencida"
BAJO_UMBRAL = "bajo_umbral"
DEUDA_DE_INTERESES = "deuda_de_intereses"
MOROSO_CRITICO = "moroso_critico"
CON_DEUDA_VENCIDA = "con_deuda_vencida"


@dataclass(frozen=True)
class SituacionDeCobranza:
    """`total_vencido`: residual de capital e interés de las obligaciones vencidas, sin restar el
    crédito a favor. `liquidaciones_vencidas`: las vencidas con capital residual (E7, E8)."""

    total_vencido: Dinero
    liquidaciones_vencidas: int
    bajo_umbral: bool
    deuda_de_intereses: bool
    moroso_critico: bool
    etiqueta: str


def clasificar(
    estado: EstadoDeCuenta, *, fecha: date, dias_de_gracia: int, umbral: Dinero
) -> SituacionDeCobranza:
    """Una obligación está vencida si `fecha > vencimiento + gracia` y su emisión no está anulada.
    Etiqueta única, por precedencia: sin deuda vencida, bajo el umbral, deuda de intereses, moroso
    crítico, con deuda vencida. El umbral se compara con el total de la cuenta (R30, E6: `>=`)."""
    gracia = timedelta(days=dias_de_gracia)
    capital = _CERO
    interes = _CERO
    liquidaciones = 0
    for o in estado.obligaciones:
        if o.id not in estado.obligaciones_que_cuentan or not fecha > o.vencimiento + gracia:
            continue
        de_capital = sumar(
            r
            for (oid, comp), r in estado.residual.items()
            if oid == o.id and comp != Componente.INTERES
        )
        de_interes = estado.residual.get((o.id, Componente.INTERES), _CERO)
        capital = capital + de_capital
        interes = interes + de_interes
        if de_capital > _CERO:
            liquidaciones += 1
    total = capital + interes
    bajo = total > _CERO and total < umbral
    solo_interes = not bajo and total > _CERO and capital == _CERO
    moroso = not bajo and liquidaciones >= 2
    if not total > _CERO:
        etiqueta = SIN_DEUDA_VENCIDA
    elif bajo:
        etiqueta = BAJO_UMBRAL
    elif solo_interes:
        etiqueta = DEUDA_DE_INTERESES
    elif moroso:
        etiqueta = MOROSO_CRITICO
    else:
        etiqueta = CON_DEUDA_VENCIDA
    return SituacionDeCobranza(total, liquidaciones, bajo, solo_interes, moroso, etiqueta)
