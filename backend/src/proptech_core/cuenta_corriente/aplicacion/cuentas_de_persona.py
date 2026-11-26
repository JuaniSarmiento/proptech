"""Las cuentas de persona de un edificio (4d, H-033, R32): la que recibe la deuda que el cambio de
titular le traslada al vendedor. Lecturas con las piezas del libro; no escriben."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.lecturas import FotoDeCuenta, fotos
from proptech_core.cuenta_corriente.dominio.vista_de_cuenta import (
    PeriodoDeCuenta,
    TotalesDeComponente,
    movimientos_en_orden,
    periodos_de,
)

__all__ = [
    "CuentaDePersona",
    "MovimientoDeCuenta",
    "PeriodoDeCuenta",
    "TotalesDeComponente",
    "cuenta_de_persona",
    "cuentas_de_persona",
]


@dataclass(frozen=True)
class MovimientoDeCuenta:
    id: UUID
    tipo: str
    sentido: str
    importe: Dinero
    fecha: date


@dataclass(frozen=True)
class CuentaDePersona:
    persona_id: UUID
    foto: FotoDeCuenta

    @property
    def cuenta_id(self) -> UUID:
        return self.foto.cuenta_id

    @property
    def deuda(self) -> Dinero:
        return self.foto.estado.deuda

    def periodos(self) -> list[PeriodoDeCuenta]:
        """Lo trasladado por período y componente, con lo cobrado y lo pendiente."""
        return periodos_de(self.foto.estado)

    def movimientos(self) -> list[MovimientoDeCuenta]:
        """Todos, en el orden del libro."""
        return [
            MovimientoDeCuenta(m.id, m.tipo, m.sentido, m.importe, m.fecha_valor)
            for m in movimientos_en_orden(self.foto.movimientos.values())
        ]


def cuentas_de_persona(sesion: Session, *, complejo_id: UUID) -> list[CuentaDePersona]:
    """Todas las cuentas de persona del edificio, también las que quedaron en cero, sin orden."""
    filas = sesion.execute(
        text("SELECT id, persona_id FROM cuenta WHERE complejo_id = :c AND persona_id IS NOT NULL"),
        {"c": complejo_id},
    ).all()
    por_cuenta = fotos(sesion, [UUID(str(f.id)) for f in filas])
    return [CuentaDePersona(UUID(str(f.persona_id)), por_cuenta[UUID(str(f.id))]) for f in filas]


def cuenta_de_persona(
    sesion: Session, *, complejo_id: UUID, cuenta_id: UUID
) -> CuentaDePersona | None:
    """La cuenta, si es una cuenta de persona de ese edificio (una de unidad, de otro edificio o de
    otra administración, que la RLS esconde, da `None`)."""
    fila = sesion.execute(
        text(
            "SELECT persona_id FROM cuenta WHERE id = :cuenta AND complejo_id = :c "
            "AND persona_id IS NOT NULL"
        ),
        {"cuenta": cuenta_id, "c": complejo_id},
    ).one_or_none()
    if fila is None:
        return None
    return CuentaDePersona(UUID(str(fila.persona_id)), fotos(sesion, [cuenta_id])[cuenta_id])
