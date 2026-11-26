"""El certificado de libre deuda (10b `condonacion-judicial-y-libre-deuda`, H-041, R21, D-171, D-172).

- `certificado_de_libre_deuda`: una fila por certificado emitido, con la foto de lo que el libro
  sabía a la fecha de corte (saldo, capital, intereses, interés corrido, pagos en revisión y cuotas
  que vencen después), su huella, la marca de gestión judicial (en falso hasta H-042) y el PDF tal
  como se emitió. De sólo agregar (tres triggers, D-115) y con RLS forzada por administración; las
  FK compuestas la atan a la unidad de su edificio y a quien la emitió. Nunca se reescribe: el PDF
  de un certificado es siempre el mismo.
- Suma `emitir_libre_deuda` al vocabulario de auditoría (la acción y el evento son uno solo, D-096).

Sin `ALTER` sobre ninguna tabla protegida existente; no importa `Accion`.

Revision ID: 0056
Revises: 0055
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLA = "certificado_de_libre_deuda"
_ACCION = "emitir_libre_deuda"

_DDL = r"""
CREATE TABLE certificado_de_libre_deuda (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, unidad_id UUID NOT NULL, fecha_de_corte DATE NOT NULL,
    saldo NUMERIC(14,2) NOT NULL, capital NUMERIC(14,2) NOT NULL,
    intereses NUMERIC(14,2) NOT NULL, interes_corrido NUMERIC(14,2) NOT NULL,
    en_revision JSONB NOT NULL, vencen_despues JSONB NOT NULL,
    en_gestion_judicial BOOLEAN NOT NULL DEFAULT false, huella TEXT NOT NULL,
    pdf BYTEA NOT NULL, emitido_por UUID NOT NULL,
    emitido_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT ck_certificado_importes CHECK
(saldo >= 0 AND capital >= 0 AND intereses >= 0 AND interes_corrido >= 0
 AND saldo = capital + intereses);
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT ck_certificado_huella CHECK
(huella ~ '^[0-9a-f]{64}$');
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT ck_certificado_pdf CHECK
(octet_length(pdf) > 0);
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT ck_certificado_foto CHECK
(jsonb_typeof(en_revision) = 'array' AND jsonb_typeof(vencen_despues) = 'array');
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT uq_certificado_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT fk_certificado_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT fk_certificado_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);
ALTER TABLE certificado_de_libre_deuda ADD CONSTRAINT fk_certificado_persona FOREIGN KEY
(administracion_id,emitido_por) REFERENCES persona (administracion_id,id);
CREATE INDEX ix_certificado_unidad ON certificado_de_libre_deuda
(administracion_id,unidad_id,emitido_en DESC);
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
    op.execute(_DDL)
    op.execute(_proteger(_TABLA))
    aislar_por_administracion(_TABLA, permisos="SELECT, INSERT")
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute(f'ALTER TABLE "{_TABLA}" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        f"""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "{_TABLA}") THEN
            RAISE EXCEPTION 'hay certificados de libre deuda: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute(f'DROP TABLE "{_TABLA}"')
    op.execute(f'DROP FUNCTION "fn_{_TABLA}_bloqueada"()')
    # La FK de `auditoria` impide retirar el vocabulario usado (23503), como en la `0050`.
    acciones = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(acciones.delete().where(acciones.c.nombre == _ACCION))
