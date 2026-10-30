"""Notas de crédito (R22, D-061, D-082; cambio 6, bloque 4) y cargos
particulares (R14, D-025; bloque 5), en la misma migración (design.md ·
Migration Plan, paso 2).

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- nota_de_credito (D2: tabla propia, nunca un gasto negativo suelto;
    # D5: el tope se garantiza con FOR UPDATE sobre la factura, no con un
    # CHECK — el CHECK de abajo sólo cubre el monto individual). ---
    op.execute("""
        CREATE TABLE nota_de_credito (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            gasto_id UUID NOT NULL, importe NUMERIC(14,2) NOT NULL, periodo DATE NOT NULL,
            cuit_emisor TEXT NOT NULL, punto_de_venta TEXT NOT NULL,
            tipo_de_comprobante TEXT NOT NULL, numero_de_comprobante TEXT NOT NULL,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        ALTER TABLE nota_de_credito ADD CONSTRAINT ck_nota_importe CHECK (importe > 0);
        ALTER TABLE nota_de_credito ADD CONSTRAINT ck_nota_periodo CHECK
            (extract(day FROM periodo) = 1);
        ALTER TABLE nota_de_credito ADD CONSTRAINT uq_nota_factura UNIQUE
            (complejo_id, cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante);
        ALTER TABLE nota_de_credito ADD CONSTRAINT fk_nota_complejo FOREIGN KEY
            (administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
        ALTER TABLE nota_de_credito ADD CONSTRAINT fk_nota_gasto FOREIGN KEY
            (administracion_id, complejo_id, gasto_id)
            REFERENCES gasto (administracion_id, complejo_id, id);
        CREATE INDEX ix_nota_gasto ON nota_de_credito (administracion_id, gasto_id);
    """)
    aislar_por_administracion("nota_de_credito")

    # --- cargo_particular (tareas 5.1/5.2): sin grupo de reparto, ni
    # siquiera como columna (D2: la base lo hace imposible, no una
    # consulta bien escrita). Nunca se borra ni es de sólo agregar: se
    # edita en borrador, igual que `gasto`. ---
    op.execute("""
        CREATE TABLE cargo_particular (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            unidad_id UUID NOT NULL, concepto TEXT NOT NULL, importe NUMERIC(14,2) NOT NULL,
            periodo DATE NOT NULL, motivo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'borrador',
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        ALTER TABLE cargo_particular ADD CONSTRAINT ck_cargo_concepto CHECK
            (length(concepto) BETWEEN 1 AND 200 AND btrim(concepto) <> '');
        ALTER TABLE cargo_particular ADD CONSTRAINT ck_cargo_motivo CHECK
            (length(motivo) BETWEEN 1 AND 500 AND btrim(motivo) <> '');
        ALTER TABLE cargo_particular ADD CONSTRAINT ck_cargo_importe CHECK (importe > 0);
        ALTER TABLE cargo_particular ADD CONSTRAINT ck_cargo_periodo CHECK
            (extract(day FROM periodo) = 1);
        ALTER TABLE cargo_particular ADD CONSTRAINT ck_cargo_estado CHECK
            (estado IN ('borrador', 'aprobado'));
        ALTER TABLE cargo_particular ADD CONSTRAINT fk_cargo_complejo FOREIGN KEY
            (administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
        ALTER TABLE cargo_particular ADD CONSTRAINT fk_cargo_unidad FOREIGN KEY
            (administracion_id, complejo_id, unidad_id)
            REFERENCES unidad (administracion_id, complejo_id, id);
        CREATE INDEX ix_cargo_periodo ON cargo_particular (administracion_id, complejo_id, periodo);
        CREATE INDEX ix_cargo_unidad ON cargo_particular (administracion_id, unidad_id);
    """)
    aislar_por_administracion("cargo_particular")


def downgrade() -> None:
    op.execute('ALTER TABLE "cargo_particular" NO FORCE ROW LEVEL SECURITY')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "cargo_particular") THEN
            RAISE EXCEPTION 'cargo_particular tiene filas';
        END IF;
    END $$""")
    op.execute('DROP TABLE "cargo_particular"')
    op.execute('ALTER TABLE "nota_de_credito" NO FORCE ROW LEVEL SECURITY')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "nota_de_credito") THEN
            RAISE EXCEPTION 'nota_de_credito tiene filas';
        END IF;
    END $$""")
    op.execute('DROP TABLE "nota_de_credito"')
