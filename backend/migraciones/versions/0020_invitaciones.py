"""Invitaciones aisladas, lectura por resumen y eventos de acceso (D6/D7/D13)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_EVENTOS = (
    "ingreso_exitoso",
    "ingreso_fallido",
    "alta_inicial",
    "invitar_personal",
    "dar_de_alta_vecino",
    "aceptar_invitacion",
    "revocar_invitacion",
    "quitar_asignacion",
)


def upgrade() -> None:
    op.create_table(
        "invitacion",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("persona_id", sa.Uuid(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("token_resumen", postgresql.BYTEA(), nullable=False),
        sa.Column("clerk_invitacion_id", sa.Text(), nullable=True),
        sa.Column("vence", sa.DateTime(timezone=True), nullable=False),
        sa.Column("creada_por", sa.Uuid(), nullable=False),
        sa.Column(
            "creada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "persona_id"],
            ["persona.administracion_id", "persona.id"],
            name="fk_invitacion_persona",
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "creada_por"],
            ["persona.administracion_id", "persona.id"],
            name="fk_invitacion_creada_por",
        ),
        sa.CheckConstraint(
            "estado IN ('pendiente','enviada','aceptada','fallida','revocada')",
            name=op.f("ck_invitacion_estado"),
        ),
        sa.CheckConstraint(
            "clerk_invitacion_id ~ '^inv_[A-Za-z0-9]+$'",
            name=op.f("ck_invitacion_clerk_id"),
        ),
        sa.UniqueConstraint("token_resumen", name="uq_invitacion_token_resumen"),
    )
    op.create_index("ix_invitacion_persona", "invitacion", ["administracion_id", "persona_id"])
    op.create_index(
        "uq_invitacion_abierta",
        "invitacion",
        ["administracion_id", "persona_id"],
        unique=True,
        postgresql_where=sa.text("estado IN ('pendiente','enviada','fallida')"),
    )
    aislar_por_administracion("invitacion")
    op.execute(
        "CREATE POLICY invitacion_por_token ON invitacion FOR SELECT USING ("
        "token_resumen = decode(nullif(current_setting('app.invitacion_token', true), ''), 'hex') "
        "AND nullif(current_setting('app.administracion_id', true), '') IS NULL)"
    )
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # Primero el vocabulario: su FK bloquea el retroceso si ya hay historia nueva.
    # Alembic revierte toda la transacción; nunca se borra ni cambia auditoría.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
    op.execute("DROP POLICY invitacion_por_token ON invitacion")
    op.drop_table("invitacion")
