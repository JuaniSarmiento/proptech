"""El certificado de libre deuda emitido, tal como se guardó (H-041)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Certificado:
    id: UUID
    unidad_id: UUID
    fecha_de_corte: date
    emitido_en: datetime
    saldo: str
    capital: str
    intereses: str
    interes_corrido: str
    en_revision: tuple[dict[str, Any], ...]
    vencen_despues: tuple[dict[str, Any], ...]
    en_gestion_judicial: bool
    huella: str

    @property
    def libre_de_deuda(self) -> bool:
        return self.saldo == "0.00"
