"""Perfiles y vínculos de la empresa, en todos los tenants bajo LOCK (D5).

El dueño relaja FORCE sólo dentro de la transacción. Un error revierte
filas, esquema y FORCE; las políticas y los permisos de PostgreSQL no cambian.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("LOCK TABLE asignacion_rol IN ACCESS EXCLUSIVE MODE")
    op.execute("ALTER TABLE asignacion_rol NO FORCE ROW LEVEL SECURITY")
    op.execute("""
        DO $$ DECLARE repetidas bigint; BEGIN
            SELECT count(*) INTO repetidas FROM (
                SELECT 1 FROM asignacion_rol WHERE rol = 'vecino'
                GROUP BY administracion_id, persona_id, unidad_id HAVING count(*) > 1
            ) AS conflictos;
            IF repetidas > 0 THEN
                RAISE EXCEPTION 'roles de la empresa: relaciones repetidas: %', repetidas;
            END IF;
        END $$
    """)
    for nombre in ("rol_valido", "nivel_valido", "forma_por_rol"):
        op.drop_constraint("ck_asignacion_rol_" + nombre, "asignacion_rol", type_="check")
    op.add_column("asignacion_rol", sa.Column("vinculo", sa.Text(), nullable=True))
    op.execute("""
        UPDATE asignacion_rol SET
            vinculo = CASE WHEN rol = 'vecino' THEN 'propietario' ELSE NULL END,
            rol = CASE
                WHEN rol = 'titular' THEN 'super_admin'
                WHEN rol = 'colaborador' AND nivel = 'editar' THEN 'administrador'
                WHEN rol = 'colaborador' AND nivel = 'ver' THEN 'auxiliar'
                ELSE rol END
    """)
    op.drop_column("asignacion_rol", "nivel")
    op.create_check_constraint(
        "ck_asignacion_rol_rol_valido",
        "asignacion_rol",
        "rol IN ('super_admin', 'administrador', 'contador', 'auxiliar', 'consejo', 'vecino')",
    )
    op.create_check_constraint(
        "ck_asignacion_rol_vinculo_valido",
        "asignacion_rol",
        "vinculo IS NULL OR vinculo IN ('propietario', 'inquilino')",
    )
    op.create_check_constraint(
        "ck_asignacion_rol_forma_por_rol",
        "asignacion_rol",
        "(rol = 'super_admin' AND complejo_id IS NULL AND unidad_id IS NULL "
        "AND vinculo IS NULL) OR "
        "(rol IN ('administrador', 'contador') AND unidad_id IS NULL AND vinculo IS NULL) OR "
        "(rol IN ('auxiliar', 'consejo') AND complejo_id IS NOT NULL AND unidad_id IS NULL "
        "AND vinculo IS NULL) OR "
        "(rol = 'vecino' AND complejo_id IS NOT NULL AND unidad_id IS NOT NULL "
        "AND vinculo IS NOT NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_asignacion_rol_persona_unidad ON asignacion_rol "
        "(administracion_id, persona_id, unidad_id) WHERE rol = 'vecino'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_asignacion_rol_persona_alcance ON asignacion_rol "
        "(administracion_id, persona_id, complejo_id) NULLS NOT DISTINCT "
        "WHERE rol IN ('super_admin', 'administrador', 'contador', 'auxiliar')"
    )
    op.create_index(
        "ix_asignacion_rol_persona", "asignacion_rol", ["administracion_id", "persona_id"]
    )
    op.execute("ALTER TABLE asignacion_rol FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    raise NotImplementedError("El downgrade se construye en la tarea 3.3")
