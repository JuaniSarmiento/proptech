"""Detalle del interés por mora: `tramo_de_interes` (4c, design D4, D10), sin datos previos.

La `0034` crea sólo esta tabla; las del saldo inicial van en la `0035` de H-005.

Revision ID: 0034
Revises: 0033
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLA = "tramo_de_interes"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE tramo_de_interes (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            cuenta_id UUID NOT NULL, movimiento_id UUID NOT NULL,
            sentido_del_movimiento TEXT NOT NULL, desde DATE NOT NULL, hasta DATE NOT NULL,
            dias INTEGER NOT NULL, base NUMERIC(14,2) NOT NULL, tasa_mensual NUMERIC(4,2) NOT NULL,
            forma_de_calculo TEXT NOT NULL, dias_de_gracia INTEGER NOT NULL,
            configuracion_id UUID NOT NULL, registrado_en TIMESTAMPTZ NOT NULL
        );
        ALTER TABLE tramo_de_interes ADD CONSTRAINT ck_tramo_sentido CHECK
        (sentido_del_movimiento='debito');
        ALTER TABLE tramo_de_interes ADD CONSTRAINT ck_tramo_orden CHECK (hasta>=desde);
        ALTER TABLE tramo_de_interes ADD CONSTRAINT ck_tramo_dias CHECK (dias=hasta-desde+1);
        ALTER TABLE tramo_de_interes ADD CONSTRAINT ck_tramo_base CHECK (base>0);
        ALTER TABLE tramo_de_interes ADD CONSTRAINT ck_tramo_forma CHECK
        (forma_de_calculo IN ('proporcional_por_dia','mes_entero'));
        ALTER TABLE tramo_de_interes ADD CONSTRAINT ck_tramo_mes_entero CHECK
        (forma_de_calculo<>'mes_entero' OR (extract(day FROM hasta+1)=1 AND
        desde>hasta-extract(day FROM hasta)::int));
        ALTER TABLE tramo_de_interes ADD CONSTRAINT fk_tramo_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE tramo_de_interes ADD CONSTRAINT fk_tramo_movimiento FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,movimiento_id,sentido_del_movimiento) REFERENCES
        movimiento (administracion_id,complejo_id,cuenta_id,id,sentido);
        CREATE INDEX ix_tramo_movimiento ON tramo_de_interes (administracion_id,movimiento_id);
    """)
    # Patrón de `0023`: tres triggers (fila, TRUNCATE, sentencia) y RLS forzada con su política.
    op.execute(f"""
        CREATE FUNCTION fn_{_TABLA}_bloqueada() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION '{_TABLA} no admite %', TG_OP; END; $$;
        CREATE TRIGGER trg_{_TABLA}_sin_update_delete BEFORE UPDATE OR DELETE ON {_TABLA}
            FOR EACH ROW EXECUTE FUNCTION fn_{_TABLA}_bloqueada();
        CREATE TRIGGER trg_{_TABLA}_sin_truncate BEFORE TRUNCATE ON {_TABLA}
            FOR EACH STATEMENT EXECUTE FUNCTION fn_{_TABLA}_bloqueada();
        CREATE TRIGGER trg_{_TABLA}_sin_update_delete_por_sentencia BEFORE UPDATE OR DELETE ON
        {_TABLA}
            FOR EACH STATEMENT EXECUTE FUNCTION fn_{_TABLA}_bloqueada();
    """)
    aislar_por_administracion(_TABLA)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir que es reversible.
    op.execute(f'ALTER TABLE "{_TABLA}" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        f"""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "{_TABLA}") THEN
            RAISE EXCEPTION '{_TABLA} tiene filas: el detalle no puede bajarse';
        END IF;
    END $$"""  # noqa: S608
    )
    op.execute(f'DROP TABLE "{_TABLA}"')
    op.execute(f"DROP FUNCTION fn_{_TABLA}_bloqueada()")
