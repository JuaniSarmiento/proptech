"""acceso_minimo

Tablas mínimas del candado (D5, D6, D-082, cambio 2a): `administracion`,
`complejo`, `unidad`, `persona` y `asignacion_rol`. Todas con
`administracion_id NOT NULL` salvo `administracion` misma (que se aísla por
su propio `id`), RLS forzada y la política de D5 (`aislar_por_administracion`,
`migraciones/ayudas_rls.py`). Corre como `proptech_migrador`: sin
`BYPASSRLS`, así que también queda sujeto a la política (E1) — quien siembre
filas tiene que fijar su tenant a propósito, igual que la app.

Convención (B2, D5): toda tabla que cuelga de un edificio lleva
`complejo_id NOT NULL` con FK compuesta `(administracion_id, complejo_id)`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ROLES_VALIDOS = ("titular", "colaborador", "consejo", "vecino")
_NIVELES_VALIDOS = ("ver", "editar")


def upgrade() -> None:
    op.create_table(
        "administracion",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nombre", sa.Text(), nullable=False),
    )
    aislar_por_administracion("administracion", columna="id")

    op.create_table(
        "complejo",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["administracion_id"], ["administracion.id"], name="fk_complejo_administracion"
        ),
        sa.UniqueConstraint("administracion_id", "id", name="uq_complejo_administracion_id"),
    )
    aislar_por_administracion("complejo")

    op.create_table(
        "unidad",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("complejo_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id"],
            ["complejo.administracion_id", "complejo.id"],
            name="fk_unidad_complejo",
        ),
        sa.UniqueConstraint(
            "administracion_id", "complejo_id", "id", name="uq_unidad_administracion_complejo_id"
        ),
    )
    aislar_por_administracion("unidad")

    op.create_table(
        "persona",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["administracion_id"], ["administracion.id"], name="fk_persona_administracion"
        ),
        sa.CheckConstraint("email = lower(email)", name="ck_persona_email_minuscula"),
        sa.UniqueConstraint("administracion_id", "id", name="uq_persona_administracion_id"),
        sa.UniqueConstraint("administracion_id", "email", name="uq_persona_administracion_email"),
    )
    aislar_por_administracion("persona")

    roles_sql = ", ".join(f"'{r}'" for r in _ROLES_VALIDOS)
    niveles_sql = ", ".join(f"'{n}'" for n in _NIVELES_VALIDOS)
    op.create_table(
        "asignacion_rol",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("persona_id", sa.Uuid(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("complejo_id", sa.Uuid(), nullable=True),
        sa.Column("unidad_id", sa.Uuid(), nullable=True),
        sa.Column("nivel", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["administracion_id", "persona_id"],
            ["persona.administracion_id", "persona.id"],
            name="fk_asignacion_rol_persona",
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id"],
            ["complejo.administracion_id", "complejo.id"],
            name="fk_asignacion_rol_complejo",
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id", "unidad_id"],
            ["unidad.administracion_id", "unidad.complejo_id", "unidad.id"],
            name="fk_asignacion_rol_unidad",
        ),
        sa.CheckConstraint(f"rol IN ({roles_sql})", name="ck_asignacion_rol_rol_valido"),
        sa.CheckConstraint(
            f"nivel IS NULL OR nivel IN ({niveles_sql})", name="ck_asignacion_rol_nivel_valido"
        ),
        sa.CheckConstraint(
            "(rol = 'titular' AND complejo_id IS NULL AND unidad_id IS NULL "
            "AND nivel IS NULL) OR "
            "(rol = 'colaborador' AND complejo_id IS NOT NULL AND unidad_id IS NULL "
            "AND nivel IS NOT NULL) OR "
            "(rol = 'consejo' AND complejo_id IS NOT NULL AND unidad_id IS NULL "
            "AND nivel IS NULL) OR "
            "(rol = 'vecino' AND complejo_id IS NOT NULL AND unidad_id IS NOT NULL "
            "AND nivel IS NULL)",
            name="ck_asignacion_rol_forma_por_rol",
        ),
    )
    aislar_por_administracion("asignacion_rol")


def downgrade() -> None:
    op.drop_table("asignacion_rol")
    op.drop_table("persona")
    op.drop_table("unidad")
    op.drop_table("complejo")
    op.drop_table("administracion")
