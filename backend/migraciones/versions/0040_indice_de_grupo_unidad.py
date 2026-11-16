"""Índice de `grupo_unidad` por edificio (7, H-011, DBA-2, E16).

La preliquidación lee la composición de todos los grupos de un edificio: sin este índice, esa
lectura recorre la tabla entera de todas las administraciones. Va por `(administracion_id,
complejo_id, grupo_id)`, el mismo prefijo que usan las demás tablas del edificio. Sin tablas
nuevas y sin tocar ninguna tabla protegida.

Revision ID: 0040
Revises: 0039
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_INDICE = "ix_grupo_unidad_edificio"


def upgrade() -> None:
    op.create_index(
        _INDICE, "grupo_unidad", ["administracion_id", "complejo_id", "grupo_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(_INDICE, table_name="grupo_unidad")
