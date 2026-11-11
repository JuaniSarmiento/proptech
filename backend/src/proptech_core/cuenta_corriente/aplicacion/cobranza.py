"""Situación de cobranza por cuenta y por edificio (design D6, E14).

Provisorio: el RED de 7.2 lo mide contra este esqueleto.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.lecturas import SENTENCIA_DEL_EDIFICIO
from proptech_core.cuenta_corriente.dominio.cobranza import SituacionDeCobranza

SENTENCIA_DE_COBRANZA = SENTENCIA_DEL_EDIFICIO


@dataclass(frozen=True)
class SituacionDeCuenta:
    cuenta_id: UUID
    unidad_id: UUID
    situacion: SituacionDeCobranza


def situacion_de_cuenta(sesion: Session, *, cuenta_id: UUID, fecha: date) -> SituacionDeCobranza:
    return SituacionDeCobranza(Dinero("0.00"), 0, False, False, False, "sin_deuda_vencida")


def situacion_del_edificio(
    sesion: Session, *, complejo_id: UUID, fecha: date
) -> Sequence[SituacionDeCuenta]:
    return []
