"""PROVISORIO (RED de la tarea 4.2): `ajustar_saldo_inicial` todavía no hace nada."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero


@dataclass(frozen=True)
class AjusteRegistrado:
    ajuste_id: UUID
    operacion_id: UUID
    obligacion_id: UUID
    cuenta_id: UUID
    unidad_id: UUID
    importe: Dinero
    componente: str
    periodo: date
    vencimiento: date
    motivo: str
    registrado_por: UUID
    registrado_en: datetime
    repetido: bool = False


def ajustar_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    operacion_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> AjusteRegistrado:
    instante = reloj()
    return AjusteRegistrado(
        uuid4(), operacion_id, uuid4(), uuid4(), unidad_id, importe, componente,
        instante.date(), instante.date(), motivo, identidad.persona_id, instante,
    )  # fmt: skip
