"""Vocabulario de la confirmación de saldos iniciales (importacion-desde-excel, H-009, design D9).

Sólo agrega la acción `confirmar_saldos_iniciales` a `accion_de_auditoria`: la confirmación
escribe en tablas que ya existen (la carga del 4c, el estado de migración del edificio y la
importación de la `0036`). No importa `Accion`: el vocabulario de una migración no cambia con el
código vivo.

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ACCION = "confirmar_saldos_iniciales"


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # La FK de `auditoria` impide retirar el vocabulario usado (23503), como en la `0024`.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre == _ACCION))
