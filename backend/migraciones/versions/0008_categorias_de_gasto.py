"""Categorías propias por edificio y orden diferible (3a, D2).

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categoria_de_gasto",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("complejo_id", sa.Uuid(), nullable=False),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id"],
            ["complejo.administracion_id", "complejo.id"],
            name="fk_categoria_complejo",
        ),
        sa.UniqueConstraint("administracion_id", "complejo_id", "clave", name="uq_categoria_clave"),
        sa.UniqueConstraint(
            "administracion_id",
            "complejo_id",
            "orden",
            name="uq_categoria_orden",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index(
        "uq_categoria_nombre",
        "categoria_de_gasto",
        ["administracion_id", "complejo_id", sa.text("lower(nombre)")],
        unique=True,
    )
    aislar_por_administracion("categoria_de_gasto")


def downgrade() -> None:
    op.drop_table("categoria_de_gasto")
