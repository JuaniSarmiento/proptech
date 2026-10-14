"""trabajos_hechos

Tabla técnica de idempotencia de los trabajos del worker (D3): registra la
clave de idempotencia dentro de la misma transacción que el efecto del
trabajo, así una ejecución repetida con la misma clave no vuelve a aplicarlo.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trabajos_hechos",
        sa.Column("clave", sa.Text(), primary_key=True),
        sa.Column("tarea", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column(
            "hecho_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "length(clave) BETWEEN 1 AND 200", name="ck_trabajos_hechos_largo_clave"
        ),
    )


def downgrade() -> None:
    op.drop_table("trabajos_hechos")
