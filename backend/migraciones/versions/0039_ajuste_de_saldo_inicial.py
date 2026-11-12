"""Ajuste de saldo inicial: `ajuste_de_saldo_inicial` y la acción `ajustar_saldo_inicial`
(importacion-desde-excel, H-010, design D8, E11).

El ajuste es una obligación nueva sin emisión (la crea el libro con su `operacion_id`) más una fila
acá con el motivo, quién y cuándo. La tabla sigue el patrón del libro (`0035`): de sólo agregar, con
tres triggers, y RLS forzada por administración. Sin `ALTER` sobre ninguna tabla protegida. No
importa `Accion`: el vocabulario de una migración no cambia con el código vivo.

Revision ID: 0039
Revises: 0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLA = "ajuste_de_saldo_inicial"
_ACCION = "ajustar_saldo_inicial"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE ajuste_de_saldo_inicial (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            cuenta_id UUID NOT NULL, obligacion_id UUID NOT NULL, operacion_id UUID NOT NULL,
            motivo TEXT NOT NULL, registrado_por UUID NOT NULL, request_id UUID NOT NULL,
            registrado_en TIMESTAMPTZ NOT NULL
        );
        ALTER TABLE ajuste_de_saldo_inicial ADD CONSTRAINT ck_ajuste_motivo CHECK
        (char_length(motivo) BETWEEN 1 AND 500 AND motivo ~ '\\S');
        ALTER TABLE ajuste_de_saldo_inicial ADD CONSTRAINT uq_ajuste_operacion UNIQUE
        (administracion_id,operacion_id);
        ALTER TABLE ajuste_de_saldo_inicial ADD CONSTRAINT fk_ajuste_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE ajuste_de_saldo_inicial ADD CONSTRAINT fk_ajuste_obligacion FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,obligacion_id) REFERENCES obligacion
        (administracion_id,complejo_id,cuenta_id,id);
        ALTER TABLE ajuste_de_saldo_inicial ADD CONSTRAINT fk_ajuste_persona FOREIGN KEY
        (administracion_id,registrado_por) REFERENCES persona (administracion_id,id);
        CREATE INDEX ix_ajuste_obligacion ON ajuste_de_saldo_inicial
        (administracion_id,obligacion_id);
        CREATE FUNCTION fn_ajuste_de_saldo_inicial_bloqueada() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'ajuste_de_saldo_inicial no admite %', TG_OP;
        END; $$;
        CREATE TRIGGER trg_ajuste_de_saldo_inicial_sin_update_delete BEFORE UPDATE OR DELETE ON
        ajuste_de_saldo_inicial FOR EACH ROW EXECUTE FUNCTION
        fn_ajuste_de_saldo_inicial_bloqueada();
        CREATE TRIGGER trg_ajuste_de_saldo_inicial_sin_truncate BEFORE TRUNCATE ON
        ajuste_de_saldo_inicial FOR EACH STATEMENT EXECUTE FUNCTION
        fn_ajuste_de_saldo_inicial_bloqueada();
        CREATE TRIGGER trg_ajuste_de_saldo_inicial_sin_update_delete_por_sentencia BEFORE UPDATE OR
        DELETE ON ajuste_de_saldo_inicial FOR EACH STATEMENT EXECUTE FUNCTION
        fn_ajuste_de_saldo_inicial_bloqueada();
    """)
    aislar_por_administracion(_TABLA)
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute(f'ALTER TABLE "{_TABLA}" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "ajuste_de_saldo_inicial") THEN
            RAISE EXCEPTION 'el ajuste de saldo inicial tiene filas: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute(f'DROP TABLE "{_TABLA}"')
    op.execute("DROP FUNCTION fn_ajuste_de_saldo_inicial_bloqueada()")
    # La FK de `auditoria` impide retirar el vocabulario usado (23503), como en la `0024`.
    acciones = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(acciones.delete().where(acciones.c.nombre == _ACCION))
