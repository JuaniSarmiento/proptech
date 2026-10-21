"""Vínculo de Clerk único por administración y lectura por identidad (D2)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("persona", sa.Column("clerk_usuario_id", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_persona_clerk_usuario_id",
        "persona",
        "clerk_usuario_id ~ '^user_[A-Za-z0-9]{1,64}$'",
    )
    op.create_unique_constraint(
        "uq_persona_clerk_administracion", "persona", ["clerk_usuario_id", "administracion_id"]
    )
    op.execute(
        "CREATE POLICY persona_por_identidad_clerk ON persona FOR SELECT USING ("
        "clerk_usuario_id = nullif(current_setting('app.identidad_clerk', true), '') AND "
        "nullif(current_setting('app.administracion_id', true), '') IS NULL)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY persona_por_identidad_clerk ON persona")
    op.drop_constraint("uq_persona_clerk_administracion", "persona", type_="unique")
    op.drop_constraint("ck_persona_clerk_usuario_id", "persona", type_="check")
    op.drop_column("persona", "clerk_usuario_id")
