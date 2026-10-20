"""Consejo único por persona y edificio, sin cambiar 0017 (RR-3).

La validación de duplicados abarca todos los tenants bajo LOCK y sólo
publica su cantidad. Todo el upgrade, incluido FORCE, es transaccional.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE")
    op.execute("ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY")
    op.execute("""
        DO $$ DECLARE repetidas bigint; BEGIN
            SELECT count(*) INTO repetidas FROM (
                SELECT 1 FROM asignacion_rol WHERE rol = 'consejo'
                GROUP BY administracion_id, persona_id, complejo_id HAVING count(*) > 1
            ) AS conflictos;
            IF repetidas > 0 THEN
                RAISE EXCEPTION 'roles de la empresa: consejos repetidos: %', repetidas;
            END IF;
        END $$
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_asignacion_rol_consejo_persona_complejo ON asignacion_rol "
        "(administracion_id, persona_id, complejo_id) WHERE rol = 'consejo'"
    )
    op.execute("ALTER TABLE asignacion_rol FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("uq_asignacion_rol_consejo_persona_complejo", table_name="asignacion_rol")
