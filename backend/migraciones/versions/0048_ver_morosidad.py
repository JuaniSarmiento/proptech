"""Vocabulario de auditoría `ver_morosidad` (10a `morosidad`, H-027, E6).

Igual patrón que `0028_ver_personal.py`: sólo suma una fila de vocabulario, sin tocar ninguna tabla
protegida ni ningún trigger, así que no hace falta reasignar funciones (enmienda E11, D-129).
Leer la morosidad no se audita: la acción existe para que el vocabulario de permisos y el de
auditoría sean uno solo (D-096).

Revision ID: 0048
Revises: 0047
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_EVENTOS = ("ver_morosidad",)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # La FK de `auditoria` preserva todo evento usado (23503, D9): punto de no retorno firmado,
    # igual que `0028`.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
