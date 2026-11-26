"""Los pagos informados de una unidad que siguen sin resolver a una fecha de corte (10b, H-041).

Es una lectura. Un pago está en revisión mientras no tiene ningún evento (confirmado, rechazado o
revertido: el estado se deriva de los eventos, E2) y se transfirió hasta el corte. No resta de
ninguna deuda: sólo se lista aparte. El importe es la parte que ese pago carga a la unidad.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero


@dataclass(frozen=True)
class PagoEnRevision:
    pago_id: UUID
    importe: Dinero
    fecha_de_transferencia: date
    banco: str
    numero_de_operacion: str


def pagos_en_revision_de_la_unidad(
    sesion: Session, *, unidad_id: UUID, corte: date
) -> list[PagoEnRevision]:
    """Por fecha de transferencia y, ante empate, por identificador del pago."""
    filas = sesion.execute(
        text(
            "SELECT p.id, x.importe, p.fecha_de_transferencia, p.banco, p.numero_de_operacion "
            "FROM pago_informado p JOIN parte_de_pago x "
            "ON x.administracion_id = p.administracion_id AND x.pago_id = p.id "
            "WHERE x.unidad_id = :unidad AND p.fecha_de_transferencia <= :corte "
            "AND NOT EXISTS (SELECT 1 FROM evento_de_pago e "
            "WHERE e.administracion_id = p.administracion_id AND e.pago_id = p.id) "
            "ORDER BY p.fecha_de_transferencia, p.id"
        ),
        {"unidad": unidad_id, "corte": corte},
    ).all()
    return [
        PagoEnRevision(
            UUID(str(f.id)),
            Dinero.desde_decimal(Decimal(f.importe)),
            f.fecha_de_transferencia,
            str(f.banco),
            str(f.numero_de_operacion),
        )
        for f in filas
    ]
