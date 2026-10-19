"""Grupos de reparto y miembros del mismo edificio (3a, D2).

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grupo_de_reparto",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("complejo_id", sa.Uuid(), nullable=False),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("metodo", sa.Text(), nullable=False),
        sa.Column("es_generales", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id"],
            ["complejo.administracion_id", "complejo.id"],
            name="fk_grupo_complejo",
        ),
        sa.UniqueConstraint("administracion_id", "complejo_id", "clave", name="uq_grupo_clave"),
        sa.UniqueConstraint("administracion_id", "complejo_id", "id", name="uq_grupo_complejo_id"),
        sa.CheckConstraint(
            "metodo IN ('coeficiente', 'superficie', 'partes_iguales')", name="ck_grupo_metodo"
        ),
        sa.CheckConstraint(
            "NOT es_generales OR metodo = 'coeficiente'", name="ck_grupo_generales_coeficiente"
        ),
    )
    op.create_index(
        "uq_grupo_generales",
        "grupo_de_reparto",
        ["administracion_id", "complejo_id"],
        unique=True,
        postgresql_where=sa.text("es_generales"),
    )
    aislar_por_administracion("grupo_de_reparto")

    op.create_table(
        "grupo_unidad",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("complejo_id", sa.Uuid(), nullable=False),
        sa.Column("grupo_id", sa.Uuid(), nullable=False),
        sa.Column("unidad_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id"],
            ["complejo.administracion_id", "complejo.id"],
            name="fk_grupo_unidad_complejo",
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id", "grupo_id"],
            [
                "grupo_de_reparto.administracion_id",
                "grupo_de_reparto.complejo_id",
                "grupo_de_reparto.id",
            ],
            name="fk_grupo_unidad_grupo",
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id", "unidad_id"],
            ["unidad.administracion_id", "unidad.complejo_id", "unidad.id"],
            name="fk_grupo_unidad_unidad",
        ),
        sa.UniqueConstraint("grupo_id", "unidad_id", name="uq_grupo_unidad"),
    )
    aislar_por_administracion("grupo_unidad")


def downgrade() -> None:
    op.drop_table("grupo_unidad")
    op.drop_index("uq_grupo_generales", table_name="grupo_de_reparto")
    op.drop_table("grupo_de_reparto")
