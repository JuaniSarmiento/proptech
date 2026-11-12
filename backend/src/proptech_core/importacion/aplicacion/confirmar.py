"""PROVISORIO (RED de la tarea 3.2): `confirmar` todavía no hace nada."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.saldo_inicial import TotalesDeSaldoInicial


@dataclass(frozen=True)
class ConfirmacionRegistrada:
    importacion_id: UUID
    carga_id: UUID
    estado_migracion: str
    totales: TotalesDeSaldoInicial
    confirmada_por: UUID
    confirmada_en: datetime


def confirmar(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    importacion_id: UUID,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> ConfirmacionRegistrada:
    cero = Dinero("0.00")
    return ConfirmacionRegistrada(
        importacion_id,
        uuid4(),
        "pendiente",
        TotalesDeSaldoInicial(cero, cero, cero),
        identidad.persona_id,
        reloj(),
    )
