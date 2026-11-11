"""Situación de cobranza de una cuenta, sin base (R20, R30, D-109.4, D-143; design D6).

Provisorio: el RED de 7.1 lo mide contra este esqueleto, que siempre dice "sin deuda".
"""

from dataclasses import dataclass
from datetime import date

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.estado import EstadoDeCuenta


@dataclass(frozen=True)
class SituacionDeCobranza:
    total_vencido: Dinero
    liquidaciones_vencidas: int
    bajo_umbral: bool
    deuda_de_intereses: bool
    moroso_critico: bool
    etiqueta: str


def clasificar(
    estado: EstadoDeCuenta, *, fecha: date, dias_de_gracia: int, umbral: Dinero
) -> SituacionDeCobranza:
    return SituacionDeCobranza(Dinero("0.00"), 0, False, False, False, "sin_deuda_vencida")
