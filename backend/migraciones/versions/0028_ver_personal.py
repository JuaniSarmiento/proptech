"""Vocabulario de auditoría `ver_personal` (2d, grupo 7, tarea 7.1, D13/E11).

Número provisorio: el 3d (Gianfranco) y el 6 (Emiliano) corren en paralelo
sobre la misma cabeza `0027`; el que mergea segundo renumera y verifica
`alembic heads`.

Igual patrón que `0024_correccion_auditada.py` y `0027_editar_edificio.py`:
sólo suma una fila de vocabulario, sin tocar ninguna tabla protegida ni
ningún trigger — no hace falta reasignar funciones (enmienda E11, D-129).

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_EVENTOS = ("ver_personal",)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # La FK de `auditoria` preserva todo evento usado (23503, D9): punto de
    # no retorno firmado, igual que `0024` y `0027`.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
