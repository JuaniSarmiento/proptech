"""La factura con QR de ARCA (lectura-de-facturas, H-036, D-169, R12).

- `gasto` deja anulables `concepto`, `categoria_id`, `grupo_id`, `periodo`, `periodo_de_imputacion`
e
  `importe`: un borrador leído del QR no trae lo que el QR no dice, y uno sin QR no trae nada. Las
  restricciones del 6 que valen con datos presentes se conservan (un `CHECK` con `NULL` no falla) y
  se suma `ck_gasto_aprobado_completo`: un gasto aprobado tiene todos esos datos, también por SQL.
- `gasto` suma `fecha_de_factura`, `origen` (`manual` para los del 6, `qr`, `sin_qr`) y
  `motivo_sin_qr`; `ck_gasto_origen` los mantiene coherentes (un `sin_qr` siempre lleva su motivo y
  los demás nunca; uno `qr` siempre lleva su fecha).
- `factura_de_gasto`: los bytes de la factura tal como se subieron, con su SHA-256, tipo y tamaño.
De
  sólo agregar (tres triggers, D-115) y con RLS forzada por administración; una por gasto. Sólo se
  baja con un enlace firmado, nunca con un `GET` autenticado.

Sin `ALTER` sobre ninguna tabla protegida existente; no importa `Accion`.

Revision ID: 0054
Revises: 0053
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ANULABLES = (
    "concepto",
    "categoria_id",
    "grupo_id",
    "periodo",
    "periodo_de_imputacion",
    "importe",
)
_MOTIVOS = (
    "no_hay_qr",
    "dominio_ajeno",
    "version_desconocida",
    "json_invalido",
    "importe_invalido",
    "datos_invalidos",
)

_DDL = r"""
CREATE TABLE factura_de_gasto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, gasto_id UUID NOT NULL, contenido BYTEA NOT NULL,
    sha256 TEXT NOT NULL, tipo TEXT NOT NULL, tamano INTEGER NOT NULL, subido_por UUID NOT NULL,
    subido_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE factura_de_gasto ADD CONSTRAINT ck_factura_tipo CHECK (tipo IN ('jpeg','png','pdf'));
ALTER TABLE factura_de_gasto ADD CONSTRAINT ck_factura_sha256 CHECK (sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE factura_de_gasto ADD CONSTRAINT ck_factura_tamano CHECK
(tamano = octet_length(contenido) AND tamano BETWEEN 1 AND 10485760);
ALTER TABLE factura_de_gasto ADD CONSTRAINT uq_factura_gasto UNIQUE (administracion_id, gasto_id);
ALTER TABLE factura_de_gasto ADD CONSTRAINT fk_factura_complejo FOREIGN KEY
(administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
ALTER TABLE factura_de_gasto ADD CONSTRAINT fk_factura_gasto FOREIGN KEY
(administracion_id, complejo_id, gasto_id) REFERENCES gasto (administracion_id, complejo_id, id);
ALTER TABLE factura_de_gasto ADD CONSTRAINT fk_factura_persona FOREIGN KEY
(administracion_id, subido_por) REFERENCES persona (administracion_id, id);
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
    for columna in _ANULABLES:
        op.execute(f"ALTER TABLE gasto ALTER COLUMN {columna} DROP NOT NULL")
    op.execute(
        "ALTER TABLE gasto ADD COLUMN fecha_de_factura DATE, "
        "ADD COLUMN origen TEXT NOT NULL DEFAULT 'manual', ADD COLUMN motivo_sin_qr TEXT"
    )
    motivos = ", ".join(f"'{m}'" for m in _MOTIVOS)
    op.execute(
        "ALTER TABLE gasto ADD CONSTRAINT ck_gasto_origen CHECK ("
        "origen IN ('manual','qr','sin_qr') "
        "AND ((origen = 'sin_qr') = (motivo_sin_qr IS NOT NULL)) "
        f"AND (motivo_sin_qr IS NULL OR motivo_sin_qr IN ({motivos})) "
        "AND (origen <> 'qr' OR fecha_de_factura IS NOT NULL))"
    )
    op.execute(
        "ALTER TABLE gasto ADD CONSTRAINT ck_gasto_aprobado_completo CHECK (estado <> 'aprobado' "
        "OR num_nonnulls(concepto, categoria_id, grupo_id, periodo, periodo_de_imputacion, "
        "importe) = 6)"
    )
    op.execute(_DDL)
    op.execute(_proteger("factura_de_gasto"))
    aislar_por_administracion("factura_de_gasto")


def downgrade() -> None:
    op.execute('ALTER TABLE "factura_de_gasto" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "factura_de_gasto") THEN
            RAISE EXCEPTION 'hay facturas guardadas: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute('DROP TABLE "factura_de_gasto"')
    op.execute('DROP FUNCTION "fn_factura_de_gasto_bloqueada"()')
    op.execute("ALTER TABLE gasto DROP CONSTRAINT ck_gasto_aprobado_completo")
    op.execute("ALTER TABLE gasto DROP CONSTRAINT ck_gasto_origen")
    op.execute("ALTER TABLE gasto NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM gasto WHERE origen <> 'manual') THEN
            RAISE EXCEPTION 'hay gastos leídos de una factura: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute("ALTER TABLE gasto FORCE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE gasto DROP COLUMN motivo_sin_qr, DROP COLUMN origen, "
        "DROP COLUMN fecha_de_factura"
    )
    for columna in reversed(_ANULABLES):
        op.execute(f"ALTER TABLE gasto ALTER COLUMN {columna} SET NOT NULL")
