"""La marca de gasto mensual obligatorio (D7, gastos-y-cargos, bloque 6).

P37 resuelta por Emiliano el 28/10/2026 (D-132): la marca vive en
`categoria_de_gasto`, no en el proveedor — "el consorcio gasta todos los
meses" con independencia de quién lo factura. Columna aditiva, `DEFAULT
false`: ninguna categoría existente queda marcada obligatoria.

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE categoria_de_gasto "
        "ADD COLUMN obligatorio_mensual BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE categoria_de_gasto DROP COLUMN obligatorio_mensual")
