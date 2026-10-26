"""Vocabulario del padrón.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_EVENTOS = (
    "crear_unidad",
    "editar_unidad",
    "crear_grupo",
    "editar_grupo",
    "fijar_unidades",
    "editar_categoria",
    "reordenar_categorias",
)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # La FK 23503 preserva todo evento utilizado: punto de no retorno firmado.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
