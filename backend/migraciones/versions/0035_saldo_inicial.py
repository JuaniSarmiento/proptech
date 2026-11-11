"""Saldo inicial: `carga_de_saldo_inicial` y `origen_de_saldo_inicial` (4c, design D5, D10).

Sin datos previos. La `0034` creó `tramo_de_interes`; estas dos tablas siguen el mismo patrón del
libro (`0023`): de sólo agregar, con tres triggers y RLS forzada por administración.

Revision ID: 0035
Revises: 0034
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLAS = ("carga_de_saldo_inicial", "origen_de_saldo_inicial")


def upgrade() -> None:
    op.execute("""
        CREATE TABLE carga_de_saldo_inicial (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            operacion_id UUID NOT NULL, fecha_de_migracion DATE NOT NULL, origen TEXT NOT NULL,
            archivo TEXT, motivo TEXT, firma_del_pedido TEXT NOT NULL,
            registrado_por UUID NOT NULL, request_id UUID NOT NULL,
            registrado_en TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE origen_de_saldo_inicial (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            carga_id UUID NOT NULL, cuenta_id UUID NOT NULL, fila INTEGER,
            obligacion_id UUID, movimiento_id UUID, sentido_del_movimiento TEXT
        );
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT ck_carga_origen CHECK
        ((origen='importador' AND archivo IS NOT NULL) OR (origen='manual' AND motivo IS NOT NULL));
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT ck_carga_firma CHECK
        (firma_del_pedido ~ '^v1:[0-9a-f]{64}$');
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT uq_carga_complejo UNIQUE
        (administracion_id,complejo_id);
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT uq_carga_operacion UNIQUE
        (administracion_id,operacion_id);
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT uq_carga_edificio_id UNIQUE
        (administracion_id,complejo_id,id);
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT fk_carga_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE carga_de_saldo_inicial ADD CONSTRAINT fk_carga_persona FOREIGN KEY
        (administracion_id,registrado_por) REFERENCES persona (administracion_id,id);
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT ck_origen_referencia CHECK
        (num_nonnulls(obligacion_id,movimiento_id)=1);
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT ck_origen_fila CHECK
        (fila IS NULL OR fila>=1);
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT ck_origen_sentido CHECK
        ((movimiento_id IS NULL)=(sentido_del_movimiento IS NULL));
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT fk_origen_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT fk_origen_carga FOREIGN KEY
        (administracion_id,complejo_id,carga_id) REFERENCES carga_de_saldo_inicial
        (administracion_id,complejo_id,id);
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT fk_origen_obligacion FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,obligacion_id) REFERENCES obligacion
        (administracion_id,complejo_id,cuenta_id,id);
        ALTER TABLE origen_de_saldo_inicial ADD CONSTRAINT fk_origen_movimiento FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,movimiento_id,sentido_del_movimiento) REFERENCES
        movimiento (administracion_id,complejo_id,cuenta_id,id,sentido);
        CREATE INDEX ix_origen_carga ON origen_de_saldo_inicial (administracion_id,carga_id);
    """)
    # Patrón de `0023`: tres triggers (fila, TRUNCATE, sentencia) y RLS forzada con su política.
    for tabla in _TABLAS:
        op.execute(f"""
            CREATE FUNCTION fn_{tabla}_bloqueada() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION '{tabla} no admite %', TG_OP; END; $$;
            CREATE TRIGGER trg_{tabla}_sin_update_delete BEFORE UPDATE OR DELETE ON {tabla}
                FOR EACH ROW EXECUTE FUNCTION fn_{tabla}_bloqueada();
            CREATE TRIGGER trg_{tabla}_sin_truncate BEFORE TRUNCATE ON {tabla}
                FOR EACH STATEMENT EXECUTE FUNCTION fn_{tabla}_bloqueada();
            CREATE TRIGGER trg_{tabla}_sin_update_delete_por_sentencia BEFORE UPDATE OR DELETE ON
            {tabla}
                FOR EACH STATEMENT EXECUTE FUNCTION fn_{tabla}_bloqueada();
        """)
        aislar_por_administracion(tabla)


def downgrade() -> None:
    # Bajan juntas y vacías: el dueño sin tenant debe ver TODAS las filas antes de decidir.
    for tabla in reversed(_TABLAS):
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "origen_de_saldo_inicial")
           OR EXISTS (SELECT 1 FROM "carga_de_saldo_inicial") THEN
            RAISE EXCEPTION 'el saldo inicial tiene filas: la carga no puede bajarse';
        END IF;
    END $$"""
    )
    for tabla in reversed(_TABLAS):
        op.execute(f'DROP TABLE "{tabla}"')
        op.execute(f"DROP FUNCTION fn_{tabla}_bloqueada()")
