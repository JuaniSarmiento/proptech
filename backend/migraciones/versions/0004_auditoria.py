"""auditoria

Auditoría de acciones sensibles (D9, cambio 2a): `accion_de_auditoria` (técnica,
del migrador, una fila por miembro de `Accion`) y `auditoria` (aislada por D5,
nunca editable ni borrable). El migrador la crea y queda como dueño transitorio;
el paso de roles `despues` (D2) se la transfiere al rol de arranque, único que
podría desactivar el trigger y el `FORCE` — y ningún servicio permanente tiene
su contraseña.

`aislar_por_administracion("auditoria", permisos="SELECT, INSERT")` documenta
que la app no debería tener `UPDATE`/`DELETE`, pero el `ALTER DEFAULT
PRIVILEGES` de `roles.antes()` se los da igual por ser una tabla nueva del
migrador: el `REVOKE` real es responsabilidad de `roles.despues()`, no de esta
migración (D9).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_NOMBRE_FUNCION_TRIGGER = "fn_auditoria_bloqueada"
_NOMBRE_TRIGGER_FILA = "trg_auditoria_sin_update_delete"
_NOMBRE_TRIGGER_SENTENCIA = "trg_auditoria_sin_truncate"

# D14: foto literal del vocabulario del 2a, independiente del enum vivo.
_ACCIONES_DEL_2A = (
    "cargar_gastos_y_preparar_liquidacion",
    "emitir_y_distribuir_liquidacion",
    "anular_liquidacion",
    "confirmar_pago_informado",
    "revertir_o_reimputar_pago",
    "condonar_intereses",
    "dar_de_baja_deuda",
    "aceptar_alertas_no_bloqueantes",
    "aceptar_alertas_bloqueantes",
    "invitar_usuarios_y_asignar_edificios",
    "informar_pago",
)


def upgrade() -> None:
    op.create_table(
        "accion_de_auditoria",
        sa.Column("nombre", sa.Text(), primary_key=True),
    )
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": nombre} for nombre in _ACCIONES_DEL_2A],
    )

    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("administracion_id", sa.Uuid(), nullable=False),
        sa.Column("persona_id", sa.Uuid(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("entidad", sa.Text(), nullable=False),
        sa.Column("entidad_id", sa.Uuid(), nullable=False),
        sa.Column(
            "detalle",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["accion"], ["accion_de_auditoria.nombre"], name="fk_auditoria_accion"
        ),
    )
    aislar_por_administracion("auditoria", permisos="SELECT, INSERT")

    # Un trigger BEFORE UPDATE OR DELETE por fila y uno BEFORE TRUNCATE por
    # sentencia levantan una excepción para CUALQUIER rol (D9), incluido el
    # dueño: ser dueño sólo da la posibilidad de desactivar el trigger
    # (ALTER TABLE ... DISABLE TRIGGER), no la de saltearlo mientras está
    # activo.
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_NOMBRE_FUNCION_TRIGGER}() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'auditoria no admite % (D9: sólo se agrega una fila, nunca se edita ni se borra)',
                TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"CREATE TRIGGER {_NOMBRE_TRIGGER_FILA} "
        f"BEFORE UPDATE OR DELETE ON auditoria "
        f"FOR EACH ROW EXECUTE FUNCTION {_NOMBRE_FUNCION_TRIGGER}()"
    )
    op.execute(
        f"CREATE TRIGGER {_NOMBRE_TRIGGER_SENTENCIA} "
        f"BEFORE TRUNCATE ON auditoria "
        f"FOR EACH STATEMENT EXECUTE FUNCTION {_NOMBRE_FUNCION_TRIGGER}()"
    )


def downgrade() -> None:
    # D9/D11: en este punto `auditoria` ya es del rol de arranque (el paso
    # `despues` corrió después del `upgrade`), así que este downgrade
    # necesita correr con ese rol, nunca con el migrador (ver
    # `_alembic_env_como_arranque` en los tests de integración y el Migration
    # Plan del design.md).
    op.execute(f"DROP TRIGGER IF EXISTS {_NOMBRE_TRIGGER_SENTENCIA} ON auditoria")
    op.execute(f"DROP TRIGGER IF EXISTS {_NOMBRE_TRIGGER_FILA} ON auditoria")
    op.execute(f"DROP FUNCTION IF EXISTS {_NOMBRE_FUNCION_TRIGGER}()")
    op.drop_table("auditoria")
    op.drop_table("accion_de_auditoria")
