"""inicial

Revision ID: 0001
Revises:
Create Date: 2026-10-09

"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
