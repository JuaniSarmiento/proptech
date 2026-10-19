"""Completa el edificio y la unidad (3a, D2).

Los defaults de relleno conservan las filas del 2a sin desactivar RLS.
Sólo estado_migracion conserva su default después de la migración.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from proptech_core.compartido.tipos_de_unidad import TIPOS_DE_UNIDAD_VALIDOS

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("complejo", sa.Column("localidad", sa.Text(), nullable=False, server_default=""))
    op.alter_column("complejo", "localidad", server_default=None)
    op.add_column(
        "complejo",
        sa.Column("estado_migracion", sa.Text(), nullable=False, server_default="pendiente"),
    )
    op.create_check_constraint(
        "ck_complejo_estado_migracion",
        "complejo",
        "estado_migracion IN ('pendiente', 'confirmada', 'sin_saldos_previos')",
    )
    op.alter_column("unidad", "nombre", new_column_name="identificador")
    op.add_column(
        "unidad", sa.Column("tipo", sa.Text(), nullable=False, server_default="departamento")
    )
    op.add_column("unidad", sa.Column("piso", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "unidad", sa.Column("coeficiente", sa.Numeric(7, 6), nullable=False, server_default="1")
    )
    op.add_column(
        "unidad", sa.Column("superficie_m2", sa.Numeric(10, 2), nullable=False, server_default="1")
    )
    op.add_column("unidad", sa.Column("estado", sa.Text(), nullable=True))
    for columna in ("tipo", "piso", "coeficiente", "superficie_m2"):
        op.alter_column("unidad", columna, server_default=None)
    tipos = ", ".join(f"'{tipo}'" for tipo in sorted(TIPOS_DE_UNIDAD_VALIDOS))
    op.create_check_constraint("ck_unidad_tipo", "unidad", f"tipo IN ({tipos})")
    op.create_check_constraint(
        "ck_unidad_coeficiente", "unidad", "coeficiente > 0 AND coeficiente <= 1"
    )
    op.create_check_constraint("ck_unidad_superficie_m2", "unidad", "superficie_m2 > 0")
    op.create_unique_constraint(
        "uq_unidad_identificador", "unidad", ["administracion_id", "complejo_id", "identificador"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_unidad_identificador", "unidad", type_="unique")
    for restriccion in ("ck_unidad_superficie_m2", "ck_unidad_coeficiente", "ck_unidad_tipo"):
        op.drop_constraint(restriccion, "unidad", type_="check")
    for columna in ("estado", "superficie_m2", "coeficiente", "piso", "tipo"):
        op.drop_column("unidad", columna)
    op.alter_column("unidad", "identificador", new_column_name="nombre")
    op.drop_constraint("ck_complejo_estado_migracion", "complejo", type_="check")
    op.drop_column("complejo", "estado_migracion")
    op.drop_column("complejo", "localidad")
