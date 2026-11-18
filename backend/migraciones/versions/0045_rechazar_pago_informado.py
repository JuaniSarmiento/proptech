"""Vocabulario de auditoría: rechazar un pago informado (pagos-informados, H-020).

`confirmar_pago_informado` ya estaba en `accion_de_auditoria` desde la `0004`; rechazar es un
evento, no un permiso, y entra acá. No importa `Accion` (L-089): la lista va literal.

Revision ID: 0045
Revises: 0044
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_EVENTOS = ("rechazar_pago_informado",)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # La FK 23503 preserva todo evento utilizado: si ya se auditó un rechazo, no se baja.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
