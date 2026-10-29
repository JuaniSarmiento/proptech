"""El documento (CUIT) propio del edificio (R12, gastos-y-cargos, tarea 3.10).

Columna aditiva y nullable: ningún edificio existente lo tiene cargado, y sin
valor el aviso de "receptor distinto" simplemente no se muestra (nunca
bloquea). Decisión confirmada por Emiliano el 28/10/2026 durante el apply
de `gastos-y-cargos` (la ambigüedad real de la tarea 3.10: no existía ningún
campo para el documento propio del edificio).

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE complejo ADD COLUMN cuit TEXT;
        ALTER TABLE complejo ADD CONSTRAINT ck_complejo_cuit CHECK
            (cuit IS NULL OR cuit ~ '^[0-9]{11}$');
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE complejo DROP COLUMN cuit")
