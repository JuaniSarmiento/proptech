"""Configuración de sólo agregar, con vencimiento coherente (3a, D2, D3).

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "configuracion_versionada",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("complejo_id", sa.Uuid(), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("tasa_mensual", sa.Numeric(4, 2), nullable=False),
        sa.Column("dias_de_gracia", sa.SmallInteger(), nullable=False),
        sa.Column("forma_de_calculo", sa.Text(), nullable=False),
        sa.Column("porcentaje_fondo", sa.Numeric(5, 2), nullable=False),
        sa.Column("dia_de_vencimiento", sa.SmallInteger(), nullable=False),
        sa.Column("modalidad_de_vencimiento", sa.Text(), nullable=False),
        sa.Column("dia_segundo_vencimiento", sa.SmallInteger(), nullable=True),
        sa.Column("recargo_segundo_vencimiento", sa.Numeric(5, 2), nullable=True),
        sa.Column("autor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "creada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "complejo_id"],
            ["complejo.administracion_id", "complejo.id"],
            name="fk_configuracion_complejo",
        ),
        sa.ForeignKeyConstraint(
            ["administracion_id", "autor_id"],
            ["persona.administracion_id", "persona.id"],
            name="fk_configuracion_autor",
        ),
        sa.UniqueConstraint(
            "administracion_id", "complejo_id", "vigente_desde", name="uq_configuracion_vigencia"
        ),
        sa.CheckConstraint("tasa_mensual BETWEEN 0 AND 10", name="ck_configuracion_tasa"),
        sa.CheckConstraint("dias_de_gracia BETWEEN 0 AND 31", name="ck_configuracion_gracia"),
        sa.CheckConstraint(
            "forma_de_calculo IN ('proporcional_por_dia', 'mes_entero')",
            name="ck_configuracion_calculo",
        ),
        sa.CheckConstraint("porcentaje_fondo BETWEEN 0 AND 100", name="ck_configuracion_fondo"),
        sa.CheckConstraint("dia_de_vencimiento BETWEEN 1 AND 28", name="ck_configuracion_dia"),
        sa.CheckConstraint(
            "modalidad_de_vencimiento IN ('unico', 'doble')", name="ck_configuracion_modalidad"
        ),
        sa.CheckConstraint(
            "recargo_segundo_vencimiento BETWEEN 0.01 AND 20.00", name="ck_configuracion_recargo"
        ),
        sa.CheckConstraint(
            "(modalidad_de_vencimiento = 'unico' AND dia_segundo_vencimiento IS NULL "
            "AND recargo_segundo_vencimiento IS NULL) OR "
            "(modalidad_de_vencimiento = 'doble' AND dia_segundo_vencimiento IS NOT NULL "
            "AND recargo_segundo_vencimiento IS NOT NULL "
            "AND dia_segundo_vencimiento > dia_de_vencimiento "
            "AND dia_segundo_vencimiento <= 28 AND recargo_segundo_vencimiento > 0)",
            name="ck_configuracion_vencimiento_coherente",
        ),
    )
    aislar_por_administracion("configuracion_versionada", permisos="SELECT, INSERT")
    # Deshacer los DEFAULT PRIVILEGES también al migrar sin el paso de roles.
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON configuracion_versionada FROM proptech_app")
    op.execute("""
        CREATE FUNCTION fn_configuracion_versionada_bloqueada() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        BEGIN
            RAISE EXCEPTION 'configuracion_versionada no admite % (sólo agregar)', TG_OP;
        END;
        $$
    """)
    op.execute(
        "CREATE TRIGGER trg_configuracion_sin_update_delete BEFORE UPDATE OR DELETE "
        "ON configuracion_versionada FOR EACH ROW "
        "EXECUTE FUNCTION fn_configuracion_versionada_bloqueada()"
    )
    op.execute(
        "CREATE TRIGGER trg_configuracion_sin_truncate BEFORE TRUNCATE "
        "ON configuracion_versionada FOR EACH STATEMENT "
        "EXECUTE FUNCTION fn_configuracion_versionada_bloqueada()"
    )


def downgrade() -> None:
    op.drop_table("configuracion_versionada")
    op.execute("DROP FUNCTION fn_configuracion_versionada_bloqueada()")
