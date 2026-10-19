"""Dos modos de coeficientes, coherentes entre grupo y miembro (3a, D15).

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "grupo_de_reparto",
        sa.Column(
            "modo_de_coeficientes", sa.Text(), nullable=False, server_default="renormalizado"
        ),
    )
    op.create_check_constraint(
        "ck_grupo_modo",
        "grupo_de_reparto",
        "modo_de_coeficientes IN ('renormalizado', 'propios')",
    )
    op.create_unique_constraint(
        "uq_grupo_modo",
        "grupo_de_reparto",
        ["administracion_id", "complejo_id", "id", "modo_de_coeficientes"],
    )
    op.create_check_constraint(
        "ck_grupo_propios_por_coeficiente",
        "grupo_de_reparto",
        "modo_de_coeficientes = 'renormalizado' OR metodo = 'coeficiente'",
    )
    op.create_check_constraint(
        "ck_grupo_generales_renormalizado",
        "grupo_de_reparto",
        "NOT es_generales OR modo_de_coeficientes = 'renormalizado'",
    )
    # Todo miembro anterior pertenece a un grupo que acaba de quedar
    # renormalizado. El DEFAULT rellena esas filas sin saltarse RLS.
    op.add_column(
        "grupo_unidad",
        sa.Column(
            "modo_de_coeficientes", sa.Text(), nullable=False, server_default="renormalizado"
        ),
    )
    op.alter_column("grupo_unidad", "modo_de_coeficientes", server_default=None)
    op.add_column("grupo_unidad", sa.Column("coeficiente", sa.Numeric(7, 6), nullable=True))
    op.create_check_constraint(
        "ck_grupo_unidad_modo_coeficiente",
        "grupo_unidad",
        "(modo_de_coeficientes = 'propios') = (coeficiente IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_grupo_unidad_coeficiente",
        "grupo_unidad",
        "coeficiente IS NULL OR (coeficiente > 0 AND coeficiente <= 1)",
    )
    op.drop_constraint("fk_grupo_unidad_grupo", "grupo_unidad", type_="foreignkey")
    op.create_foreign_key(
        "fk_grupo_unidad_grupo",
        "grupo_unidad",
        "grupo_de_reparto",
        ["administracion_id", "complejo_id", "grupo_id", "modo_de_coeficientes"],
        ["administracion_id", "complejo_id", "id", "modo_de_coeficientes"],
        onupdate="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_grupo_unidad_grupo", "grupo_unidad", type_="foreignkey")
    op.create_foreign_key(
        "fk_grupo_unidad_grupo",
        "grupo_unidad",
        "grupo_de_reparto",
        ["administracion_id", "complejo_id", "grupo_id"],
        ["administracion_id", "complejo_id", "id"],
    )
    op.drop_constraint("ck_grupo_unidad_coeficiente", "grupo_unidad", type_="check")
    op.drop_constraint("ck_grupo_unidad_modo_coeficiente", "grupo_unidad", type_="check")
    op.drop_column("grupo_unidad", "coeficiente")
    op.drop_column("grupo_unidad", "modo_de_coeficientes")
    for restriccion in (
        "ck_grupo_generales_renormalizado",
        "ck_grupo_propios_por_coeficiente",
        "ck_grupo_modo",
    ):
        op.drop_constraint(restriccion, "grupo_de_reparto", type_="check")
    op.drop_constraint("uq_grupo_modo", "grupo_de_reparto", type_="unique")
    op.drop_column("grupo_de_reparto", "modo_de_coeficientes")
