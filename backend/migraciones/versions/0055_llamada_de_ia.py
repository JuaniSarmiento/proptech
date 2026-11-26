"""La lectura de la factura con IA (lectura-de-facturas, H-037, D-169, R12, R23).

- `llamada_de_ia`: una fila por cada llamada al lector de IA, buena o fallida, con su modelo, sus
  tokens y su costo en dólares. De sólo agregar (tres triggers, D-115) y con RLS forzada por
  administración; la FK compuesta la ata al gasto de su edificio. Sin lector configurado no hay
  llamada y no hay fila.
- `gasto.lectura_ia` (JSONB, anulable): lo que dejó la lectura (`motivo`, `detalle` y los `campos`
  que completó la IA). `NULL` hasta que la tarea del worker corre.

Sin `ALTER` sobre ninguna tabla protegida existente; no importa `Accion`.

Revision ID: 0055
Revises: 0054
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_DDL = r"""
CREATE TABLE llamada_de_ia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, gasto_id UUID NOT NULL, clave TEXT NOT NULL, modelo TEXT NOT NULL,
    tokens_entrada INTEGER NOT NULL, tokens_salida INTEGER NOT NULL,
    costo_usd NUMERIC(12,6) NOT NULL, resultado TEXT NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE llamada_de_ia ADD CONSTRAINT ck_llamada_de_ia_resultado CHECK
(resultado IN ('ok', 'fallida'));
ALTER TABLE llamada_de_ia ADD CONSTRAINT ck_llamada_de_ia_uso CHECK
(tokens_entrada >= 0 AND tokens_salida >= 0 AND costo_usd >= 0);
ALTER TABLE llamada_de_ia ADD CONSTRAINT ck_llamada_de_ia_texto CHECK
(length(clave) BETWEEN 1 AND 200 AND length(modelo) BETWEEN 1 AND 200);
ALTER TABLE llamada_de_ia ADD CONSTRAINT fk_llamada_de_ia_complejo FOREIGN KEY
(administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
ALTER TABLE llamada_de_ia ADD CONSTRAINT fk_llamada_de_ia_gasto FOREIGN KEY
(administracion_id, complejo_id, gasto_id) REFERENCES gasto (administracion_id, complejo_id, id);
CREATE INDEX ix_llamada_de_ia_gasto ON llamada_de_ia (administracion_id, gasto_id, resultado);
"""


def _proteger(tabla: str) -> str:
    funcion = f"fn_{tabla}_bloqueada"
    return f"""
CREATE FUNCTION {funcion}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION '{tabla} no admite %', TG_OP;
END; $$;
CREATE TRIGGER trg_{tabla}_sin_update_delete BEFORE UPDATE OR DELETE ON {tabla}
FOR EACH ROW EXECUTE FUNCTION {funcion}();
CREATE TRIGGER trg_{tabla}_sin_truncate BEFORE TRUNCATE ON {tabla}
FOR EACH STATEMENT EXECUTE FUNCTION {funcion}();
CREATE TRIGGER trg_{tabla}_sin_update_delete_por_sentencia BEFORE UPDATE OR DELETE ON {tabla}
FOR EACH STATEMENT EXECUTE FUNCTION {funcion}();
"""


def upgrade() -> None:
    op.execute("ALTER TABLE gasto ADD COLUMN lectura_ia JSONB")
    op.execute(_DDL)
    op.execute(_proteger("llamada_de_ia"))
    aislar_por_administracion("llamada_de_ia", permisos="SELECT, INSERT")


def downgrade() -> None:
    op.execute('ALTER TABLE "llamada_de_ia" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "llamada_de_ia") THEN
            RAISE EXCEPTION 'hay llamadas de IA registradas: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute('DROP TABLE "llamada_de_ia"')
    op.execute('DROP FUNCTION "fn_llamada_de_ia_bloqueada"()')
    op.execute("ALTER TABLE gasto DROP COLUMN lectura_ia")
