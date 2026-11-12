"""Borrador de saldos: `fila_de_saldo_importada`, `control_de_saldo` y `aceptacion_de_diferencias`
(importacion-desde-excel, design D5, D6, D10) y la acción `aceptar_diferencias_de_saldos`.

Las filas del borrador y el control cuelgan de la `importacion` de la `0036` y de la unidad, con FK
compuestas que fijan edificio y administración; la app las cambia (RLS forzada). La aceptación es de
sólo agregar, con el patrón del libro (`0035`): tres triggers, RLS forzada por administración y el
arranque de dueño (lo transfiere `roles despues`). Una por importación: aceptar dos veces el mismo
borrador lo frena la base, además del candado del complejo.

Revision ID: 0037
Revises: 0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ACCION = "aceptar_diferencias_de_saldos"
_TABLAS = ("fila_de_saldo_importada", "control_de_saldo", "aceptacion_de_diferencias")


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fila_de_saldo_importada (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            importacion_id UUID NOT NULL, unidad_id UUID NOT NULL,
            fila INTEGER NOT NULL, tipo TEXT NOT NULL,
            periodo DATE, vencimiento DATE, concepto TEXT,
            importe NUMERIC(14,2) NOT NULL, interes_acumulado NUMERIC(14,2) NOT NULL DEFAULT 0
        );
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_fila CHECK (fila >= 2);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_tipo CHECK
            (tipo IN ('detalle', 'total', 'credito'));
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_concepto CHECK
            (concepto IS NULL OR concepto IN ('ordinaria', 'fondo_de_reserva', 'extraordinaria'));
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_importes CHECK
            (importe >= 0 AND interes_acumulado >= 0);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_periodo_dia_1 CHECK
            (periodo IS NULL OR periodo = date_trunc('month', periodo)::date);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_forma CHECK (
            (tipo = 'detalle' AND periodo IS NOT NULL AND vencimiento IS NOT NULL
                AND concepto IS NOT NULL)
            OR (tipo IN ('total', 'credito') AND periodo IS NULL AND vencimiento IS NULL
                AND concepto IS NULL)
        );
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT ck_fila_de_saldo_credito_sin_interes
            CHECK (tipo <> 'credito' OR interes_acumulado = 0);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT uq_fila_de_saldo_fila UNIQUE
            (administracion_id, importacion_id, fila);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT fk_fila_de_saldo_complejo
            FOREIGN KEY (administracion_id, complejo_id)
            REFERENCES complejo (administracion_id, id);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT fk_fila_de_saldo_importacion
            FOREIGN KEY (administracion_id, complejo_id, importacion_id)
            REFERENCES importacion (administracion_id, complejo_id, id);
        ALTER TABLE fila_de_saldo_importada ADD CONSTRAINT fk_fila_de_saldo_unidad
            FOREIGN KEY (administracion_id, complejo_id, unidad_id)
            REFERENCES unidad (administracion_id, complejo_id, id);
        CREATE INDEX ix_fila_de_saldo_unidad ON fila_de_saldo_importada
            (administracion_id, importacion_id, unidad_id);

        CREATE TABLE control_de_saldo (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            importacion_id UUID NOT NULL, unidad_id UUID NOT NULL,
            fila INTEGER NOT NULL, saldo NUMERIC(14,2) NOT NULL
        );
        ALTER TABLE control_de_saldo ADD CONSTRAINT ck_control_de_saldo_fila CHECK (fila >= 2);
        ALTER TABLE control_de_saldo ADD CONSTRAINT uq_control_de_saldo_fila UNIQUE
            (administracion_id, importacion_id, fila);
        ALTER TABLE control_de_saldo ADD CONSTRAINT uq_control_de_saldo_unidad UNIQUE
            (administracion_id, importacion_id, unidad_id);
        ALTER TABLE control_de_saldo ADD CONSTRAINT fk_control_de_saldo_complejo
            FOREIGN KEY (administracion_id, complejo_id)
            REFERENCES complejo (administracion_id, id);
        ALTER TABLE control_de_saldo ADD CONSTRAINT fk_control_de_saldo_importacion
            FOREIGN KEY (administracion_id, complejo_id, importacion_id)
            REFERENCES importacion (administracion_id, complejo_id, id);
        ALTER TABLE control_de_saldo ADD CONSTRAINT fk_control_de_saldo_unidad
            FOREIGN KEY (administracion_id, complejo_id, unidad_id)
            REFERENCES unidad (administracion_id, complejo_id, id);

        CREATE TABLE aceptacion_de_diferencias (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            importacion_id UUID NOT NULL, aceptada_por UUID NOT NULL,
            aceptada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
            diferencias JSONB NOT NULL
        );
        ALTER TABLE aceptacion_de_diferencias ADD CONSTRAINT ck_aceptacion_diferencias CHECK
            (jsonb_typeof(diferencias) = 'array' AND jsonb_array_length(diferencias) > 0);
        ALTER TABLE aceptacion_de_diferencias ADD CONSTRAINT uq_aceptacion_importacion UNIQUE
            (administracion_id, importacion_id);
        ALTER TABLE aceptacion_de_diferencias ADD CONSTRAINT fk_aceptacion_complejo
            FOREIGN KEY (administracion_id, complejo_id)
            REFERENCES complejo (administracion_id, id);
        ALTER TABLE aceptacion_de_diferencias ADD CONSTRAINT fk_aceptacion_importacion
            FOREIGN KEY (administracion_id, complejo_id, importacion_id)
            REFERENCES importacion (administracion_id, complejo_id, id);
        ALTER TABLE aceptacion_de_diferencias ADD CONSTRAINT fk_aceptacion_persona
            FOREIGN KEY (administracion_id, aceptada_por)
            REFERENCES persona (administracion_id, id);
    """)
    # Sólo la aceptación es de sólo agregar: tres triggers (fila, TRUNCATE, sentencia), como `0035`.
    op.execute("""
        CREATE FUNCTION fn_aceptacion_de_diferencias_bloqueada() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'aceptacion_de_diferencias no admite %', TG_OP;
        END; $$;
        CREATE TRIGGER trg_aceptacion_de_diferencias_sin_update_delete
            BEFORE UPDATE OR DELETE ON aceptacion_de_diferencias
            FOR EACH ROW EXECUTE FUNCTION fn_aceptacion_de_diferencias_bloqueada();
        CREATE TRIGGER trg_aceptacion_de_diferencias_sin_truncate
            BEFORE TRUNCATE ON aceptacion_de_diferencias
            FOR EACH STATEMENT EXECUTE FUNCTION fn_aceptacion_de_diferencias_bloqueada();
        CREATE TRIGGER trg_aceptacion_de_diferencias_sin_update_delete_por_sentencia
            BEFORE UPDATE OR DELETE ON aceptacion_de_diferencias
            FOR EACH STATEMENT EXECUTE FUNCTION fn_aceptacion_de_diferencias_bloqueada();
    """)
    for tabla in _TABLAS:
        aislar_por_administracion(tabla)
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # Bajan juntas y vacías: el dueño sin tenant debe ver TODAS las filas antes de decidir.
    for tabla in reversed(_TABLAS):
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "aceptacion_de_diferencias")
           OR EXISTS (SELECT 1 FROM "control_de_saldo")
           OR EXISTS (SELECT 1 FROM "fila_de_saldo_importada") THEN
            RAISE EXCEPTION 'el borrador de saldos tiene filas: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    for tabla in reversed(_TABLAS):
        op.execute(f'DROP TABLE "{tabla}"')
    op.execute("DROP FUNCTION fn_aceptacion_de_diferencias_bloqueada()")
    # La FK de `auditoria` impide retirar el vocabulario usado (23503), como en la `0024`.
    tabla_de_acciones = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla_de_acciones.delete().where(tabla_de_acciones.c.nombre == _ACCION))
