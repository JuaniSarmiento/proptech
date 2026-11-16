"""El PDF de la expensa y su archivo (liquidacion-y-emision, H-015, design E12, D-060, D-160).

Se separa lo que cambia de lo que se agrega (D-115):

- `documento_de_expensa`: una fila por unidad con obligación y por variante (`completa` y
  `sin_extraordinaria`, D-106), con su estado (`pendiente`, `generado`, `fallido`) y el motivo de un
  fallo. Cambia de estado, así que **no** es de sólo agregar; un trigger la protege donde importa:
  nunca se borra, su identidad no cambia y un documento `generado` no se toca más (el archivo de las
  liquidaciones no se reescribe, CCyC art. 2067 inc. i). Pasar a `generado` exige que el PDF ya esté
  archivado.
- `pdf_de_expensa`: los bytes del PDF con su SHA-256 y la fecha. De sólo agregar, con el patrón del
  libro (`0035`, `0041`): tres triggers y RLS forzada por administración. Un PDF por documento
  (único).

La política `documento_pendiente_del_barrido` deja a la app, sin tenant y sólo si el worker declara
`app.barrido_de_documentos`, **leer** los documentos `pendiente` de cualquier administración: es el
barrido que reencola lo que quedó pendiente cuando Redis no estaba (E12). Gemela de
`invitacion_por_token` (`0020`): sólo lectura, sólo `pendiente`, y nunca toca los bytes (viven en
la otra tabla). Sin `ALTER` sobre ninguna tabla protegida existente; no importa `Accion`.

Revision ID: 0043
Revises: 0042
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_DDL = """
CREATE TABLE documento_de_expensa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, liquidacion_id UUID NOT NULL, unidad_id UUID NOT NULL,
    variante TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'pendiente', motivo TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(), actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE documento_de_expensa ADD CONSTRAINT ck_documento_variante CHECK
(variante IN ('completa','sin_extraordinaria'));
ALTER TABLE documento_de_expensa ADD CONSTRAINT ck_documento_estado CHECK
(estado IN ('pendiente','generado','fallido'));
ALTER TABLE documento_de_expensa ADD CONSTRAINT ck_documento_motivo CHECK (
    (estado = 'fallido' AND char_length(motivo) BETWEEN 1 AND 500 AND motivo ~ '\\S')
    OR (estado <> 'fallido' AND motivo IS NULL));
ALTER TABLE documento_de_expensa ADD CONSTRAINT uq_documento_unidad_variante UNIQUE
(administracion_id,liquidacion_id,unidad_id,variante);
ALTER TABLE documento_de_expensa ADD CONSTRAINT uq_documento_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE documento_de_expensa ADD CONSTRAINT fk_documento_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE documento_de_expensa ADD CONSTRAINT fk_documento_liquidacion FOREIGN KEY
(administracion_id,complejo_id,liquidacion_id) REFERENCES liquidacion
(administracion_id,complejo_id,id);
ALTER TABLE documento_de_expensa ADD CONSTRAINT fk_documento_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);
CREATE INDEX ix_documento_liquidacion ON documento_de_expensa (administracion_id,liquidacion_id);
CREATE INDEX ix_documento_pendiente ON documento_de_expensa (estado) WHERE estado = 'pendiente';

CREATE FUNCTION fn_documento_de_expensa_guarda() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'documento_de_expensa no admite DELETE';
    END IF;
    IF OLD.estado = 'generado' THEN
        RAISE EXCEPTION 'un documento generado no se modifica (CCyC art. 2067 inc. i)';
    END IF;
    IF (NEW.id, NEW.administracion_id, NEW.complejo_id, NEW.liquidacion_id, NEW.unidad_id,
        NEW.variante, NEW.creado_en)
       IS DISTINCT FROM (OLD.id, OLD.administracion_id, OLD.complejo_id, OLD.liquidacion_id,
        OLD.unidad_id, OLD.variante, OLD.creado_en) THEN
        RAISE EXCEPTION 'la identidad de un documento no cambia';
    END IF;
    IF NEW.estado = 'generado' AND NOT EXISTS (
        SELECT 1 FROM pdf_de_expensa WHERE documento_id = NEW.id) THEN
        RAISE EXCEPTION 'un documento no pasa a generado sin su PDF archivado';
    END IF;
    RETURN NEW;
END; $$;
CREATE TRIGGER trg_documento_de_expensa_guarda BEFORE UPDATE OR DELETE ON documento_de_expensa
FOR EACH ROW EXECUTE FUNCTION fn_documento_de_expensa_guarda();

CREATE TABLE pdf_de_expensa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, documento_id UUID NOT NULL, contenido BYTEA NOT NULL,
    sha256 TEXT NOT NULL, generado_en TIMESTAMPTZ NOT NULL
);
ALTER TABLE pdf_de_expensa ADD CONSTRAINT ck_pdf_contenido CHECK (octet_length(contenido) > 0);
ALTER TABLE pdf_de_expensa ADD CONSTRAINT ck_pdf_sha256 CHECK (sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE pdf_de_expensa ADD CONSTRAINT uq_pdf_documento UNIQUE (administracion_id,documento_id);
ALTER TABLE pdf_de_expensa ADD CONSTRAINT fk_pdf_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE pdf_de_expensa ADD CONSTRAINT fk_pdf_documento FOREIGN KEY
(administracion_id,complejo_id,documento_id) REFERENCES documento_de_expensa
(administracion_id,complejo_id,id);
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
    op.execute(_proteger("pdf_de_expensa"))
    aislar_por_administracion("documento_de_expensa")
    aislar_por_administracion("pdf_de_expensa")
    op.execute(
        "CREATE POLICY documento_pendiente_del_barrido ON documento_de_expensa FOR SELECT USING ("
        "estado = 'pendiente' "
        "AND nullif(current_setting('app.administracion_id', true), '') IS NULL "
        "AND current_setting('app.barrido_de_documentos', true) = 'si')"
    )


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute('ALTER TABLE "pdf_de_expensa" NO FORCE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "documento_de_expensa" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "pdf_de_expensa") OR EXISTS (SELECT 1 FROM "documento_de_expensa")
        THEN
            RAISE EXCEPTION 'hay documentos de expensa: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute('DROP TABLE "pdf_de_expensa"')
    op.execute('DROP FUNCTION "fn_pdf_de_expensa_bloqueada"()')
    op.execute('DROP TABLE "documento_de_expensa"')
    op.execute("DROP FUNCTION fn_documento_de_expensa_guarda()")
