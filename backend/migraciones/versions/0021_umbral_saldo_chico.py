"""Umbral de R30 y bloqueo por sentencia.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Default constante histórico: no UPDATE, ni reescritura de las versiones existentes.
    op.execute(
        "ALTER TABLE configuracion_versionada ADD COLUMN "
        "umbral_saldo_chico NUMERIC(14,2) NOT NULL DEFAULT 500.00"
    )
    op.execute(
        "ALTER TABLE configuracion_versionada ADD CONSTRAINT "
        "ck_configuracion_umbral CHECK (umbral_saldo_chico >= 0)"
    )
    op.execute("ALTER TABLE configuracion_versionada ALTER COLUMN umbral_saldo_chico DROP DEFAULT")
    op.execute(
        "CREATE TRIGGER trg_configuracion_sin_update_delete_por_sentencia "
        "BEFORE UPDATE OR DELETE ON configuracion_versionada FOR EACH STATEMENT "
        "EXECUTE FUNCTION fn_configuracion_versionada_bloqueada()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_configuracion_sin_update_delete_por_sentencia ON configuracion_versionada"
    )
    op.execute("ALTER TABLE configuracion_versionada DROP COLUMN umbral_saldo_chico")
