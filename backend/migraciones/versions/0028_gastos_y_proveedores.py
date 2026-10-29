"""Proveedores y gastos (R12, D-019; cambio 6 `gastos-y-cargos`).

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- proveedor (tarea 2.4): nunca se borra, sólo se desactiva (R16). ---
    op.execute("""
        CREATE TABLE proveedor (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            razon_social TEXT NOT NULL, cuit TEXT NOT NULL, activo BOOLEAN NOT NULL DEFAULT true,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        ALTER TABLE proveedor ADD CONSTRAINT ck_proveedor_razon_social CHECK
            (length(razon_social) BETWEEN 1 AND 200 AND btrim(razon_social) <> '');
        ALTER TABLE proveedor ADD CONSTRAINT ck_proveedor_cuit CHECK (cuit ~ '^[0-9]{11}$');
        ALTER TABLE proveedor ADD CONSTRAINT uq_proveedor_cuit UNIQUE (complejo_id, cuit);
        ALTER TABLE proveedor ADD CONSTRAINT fk_proveedor_complejo FOREIGN KEY
            (administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
        ALTER TABLE proveedor ADD CONSTRAINT uq_proveedor_complejo_id UNIQUE
            (administracion_id, complejo_id, id);
    """)
    aislar_por_administracion("proveedor")

    # --- gasto (tareas 3.3/3.4): D3 (clave de factura en bloque), D4 (editable
    # mientras no esté aprobado, no es tabla de sólo agregar), D9 (RLS, dueño
    # proptech_migrador por defecto: el migrador mismo crea la tabla). ---
    #
    # `categoria_de_gasto` (0008) no tenía todavía un único por
    # (administracion_id, complejo_id, id): sin él, el FK compuesto de abajo
    # no puede apoyarse. Es aditivo (toda fila ya cumple la condición, el id
    # ya es único por sí solo) y no cambia ninguna garantía existente de
    # `categorias-de-gasto` — mismo patrón que D7 del 3c con la clave
    # derivada.
    op.execute("""
        ALTER TABLE categoria_de_gasto ADD CONSTRAINT uq_categoria_complejo_id UNIQUE
            (administracion_id, complejo_id, id);
    """)
    op.execute("""
        CREATE TABLE gasto (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            proveedor_id UUID, categoria_id UUID NOT NULL, grupo_id UUID NOT NULL,
            concepto TEXT NOT NULL, periodo DATE NOT NULL,
            periodo_de_imputacion DATE NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'ordinario',
            importe NUMERIC(14,2) NOT NULL,
            estado TEXT NOT NULL DEFAULT 'borrador',
            cuit_emisor TEXT, punto_de_venta TEXT, tipo_de_comprobante TEXT,
            numero_de_comprobante TEXT, documento_receptor TEXT,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        ALTER TABLE gasto ADD CONSTRAINT ck_gasto_concepto CHECK
            (length(concepto) BETWEEN 1 AND 200 AND btrim(concepto) <> '');
        ALTER TABLE gasto ADD CONSTRAINT ck_gasto_periodo CHECK (extract(day FROM periodo) = 1);
        ALTER TABLE gasto ADD CONSTRAINT ck_gasto_tipo CHECK
            (tipo IN ('ordinario', 'extraordinario'));
        ALTER TABLE gasto ADD CONSTRAINT ck_gasto_importe CHECK (importe > 0);
        ALTER TABLE gasto ADD CONSTRAINT ck_gasto_estado CHECK
            (estado IN ('borrador', 'sin_ia', 'en_revision', 'aprobado'));
        ALTER TABLE gasto ADD CONSTRAINT ck_gasto_factura CHECK
            (num_nonnulls(cuit_emisor, punto_de_venta, tipo_de_comprobante,
                          numero_de_comprobante) IN (0, 4));
        ALTER TABLE gasto ADD CONSTRAINT uq_gasto_factura UNIQUE
            (complejo_id, cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante);
        ALTER TABLE gasto ADD CONSTRAINT fk_gasto_complejo FOREIGN KEY
            (administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
        ALTER TABLE gasto ADD CONSTRAINT fk_gasto_categoria FOREIGN KEY
            (administracion_id, complejo_id, categoria_id)
            REFERENCES categoria_de_gasto (administracion_id, complejo_id, id);
        ALTER TABLE gasto ADD CONSTRAINT fk_gasto_grupo FOREIGN KEY
            (administracion_id, complejo_id, grupo_id)
            REFERENCES grupo_de_reparto (administracion_id, complejo_id, id);
        ALTER TABLE gasto ADD CONSTRAINT fk_gasto_proveedor FOREIGN KEY
            (administracion_id, complejo_id, proveedor_id)
            REFERENCES proveedor (administracion_id, complejo_id, id);
        CREATE INDEX ix_gasto_periodo ON gasto (administracion_id, complejo_id, periodo);
        CREATE INDEX ix_gasto_grupo ON gasto (administracion_id, grupo_id);
        -- Único para que `nota_de_credito` (bloque 4) pueda FK-ear compuesto
        -- contra el edificio, mismo patrón que `uq_proveedor_complejo_id`.
        ALTER TABLE gasto ADD CONSTRAINT uq_gasto_complejo_id UNIQUE
            (administracion_id, complejo_id, id);
    """)
    aislar_por_administracion("gasto")


def downgrade() -> None:
    op.execute('ALTER TABLE "gasto" NO FORCE ROW LEVEL SECURITY')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "gasto") THEN
            RAISE EXCEPTION 'gasto tiene filas';
        END IF;
    END $$""")
    op.execute('DROP TABLE "gasto"')
    op.execute("ALTER TABLE categoria_de_gasto DROP CONSTRAINT uq_categoria_complejo_id")
    op.execute('ALTER TABLE "proveedor" NO FORCE ROW LEVEL SECURITY')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "proveedor") THEN
            RAISE EXCEPTION 'proveedor tiene filas';
        END IF;
    END $$""")
    op.execute('DROP TABLE "proveedor"')
