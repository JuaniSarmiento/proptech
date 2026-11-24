"""Vocabulario de auditoría `exportar_morosidad` (10a `morosidad`, H-028, E8).

Igual patrón que `0048_ver_morosidad.py`: sólo suma una fila de vocabulario, sin tocar ninguna
tabla protegida ni ningún trigger (enmienda E11, D-129). Exportar la morosidad no se audita: la
acción existe para que el vocabulario de permisos y el de auditoría sean uno solo (D-096).

Revision ID: 0049
Revises: 0048
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_EVENTOS = ("exportar_morosidad",)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # La FK de `auditoria` preserva todo evento usado (23503, D9): punto de no retorno firmado,
    # igual que `0048`.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
