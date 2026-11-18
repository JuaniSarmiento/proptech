"""Los pagos informados por el vecino (pagos-informados, H-018, design E2 y E3, D-163, D-165).

Seis tablas de sólo agregar (D-115): tres triggers cada una y RLS forzada por administración, y a
cargo del rol de arranque cuando corre `roles despues`.

- `comprobante_de_pago`: los bytes del comprobante con su SHA-256, su tipo y tamaño, quién lo
  subió y lo que leyó la IA (`lectura`, `propuesta`; H-019).
- `pago_informado`: el pago con banco y número tal como vinieron y normalizados, la fecha de la
  transferencia, el monto y el CBU de origen. El comprobante es de un solo pago.
- `parte_de_pago`: una parte por unidad; la base exige que sea del mismo edificio que el pago.
- `evento_de_pago`: `confirmado`, `rechazado`, `revertido`, `reimputado`. El estado del pago se
  deriva del último evento. Un solo `confirmado` o `rechazado` por pago y un solo `revertido`.
- `movimiento_de_pago` y `cbu_de_unidad`: los usan H-020 y los siguientes; nacen vacías.

El número de operación es único por edificio, banco y número (normalizados) entre los pagos sin
evento `rechazado` (D-163). Un índice único parcial no puede mirar otra tabla, así que lo frena un
trigger `BEFORE INSERT` sobre `pago_informado` que toma un candado de transacción por clave y revisa
(D-165): dos INSERT simultáneos de la misma clave se serializan y el segundo ve al primero. Un
rechazo libera el número por INSERT de su evento, sin tocar ninguna fila. La función nombra las
tablas con `public.`: corre con el `search_path` de la sesión de la app, que no lo incluye.

Sin `ALTER` sobre ninguna tabla protegida existente; no importa `Accion`.

Revision ID: 0044
Revises: 0043
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLAS = (
    "comprobante_de_pago",
    "pago_informado",
    "parte_de_pago",
    "evento_de_pago",
    "movimiento_de_pago",
    "cbu_de_unidad",
)

_DDL = r"""
CREATE TABLE comprobante_de_pago (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, contenido BYTEA NOT NULL, sha256 TEXT NOT NULL, tipo TEXT NOT NULL,
    tamano INTEGER NOT NULL, subido_por UUID NOT NULL,
    subido_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    lectura TEXT NOT NULL DEFAULT 'sin_ia', propuesta JSONB
);
ALTER TABLE comprobante_de_pago ADD CONSTRAINT ck_comprobante_tipo CHECK
(tipo IN ('jpeg','png','pdf'));
ALTER TABLE comprobante_de_pago ADD CONSTRAINT ck_comprobante_sha256 CHECK
(sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE comprobante_de_pago ADD CONSTRAINT ck_comprobante_tamano CHECK
(tamano = octet_length(contenido) AND tamano BETWEEN 1 AND 10485760);
ALTER TABLE comprobante_de_pago ADD CONSTRAINT ck_comprobante_lectura CHECK
(lectura IN ('ok','fallida','sin_ia'));
ALTER TABLE comprobante_de_pago ADD CONSTRAINT uq_comprobante_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE comprobante_de_pago ADD CONSTRAINT fk_comprobante_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE comprobante_de_pago ADD CONSTRAINT fk_comprobante_persona FOREIGN KEY
(administracion_id,subido_por) REFERENCES persona (administracion_id,id);

CREATE TABLE pago_informado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, comprobante_id UUID NOT NULL,
    banco TEXT NOT NULL, banco_normalizado TEXT NOT NULL,
    numero_de_operacion TEXT NOT NULL, numero_normalizado TEXT NOT NULL,
    fecha_de_transferencia DATE NOT NULL, monto NUMERIC(14,2) NOT NULL, cbu_origen TEXT,
    informado_por UUID NOT NULL, informado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE pago_informado ADD CONSTRAINT ck_pago_monto CHECK (monto > 0);
ALTER TABLE pago_informado ADD CONSTRAINT ck_pago_banco CHECK
(char_length(banco) BETWEEN 1 AND 100 AND btrim(banco) <> '' AND banco_normalizado <> '');
ALTER TABLE pago_informado ADD CONSTRAINT ck_pago_numero CHECK
(char_length(numero_de_operacion) BETWEEN 1 AND 100 AND btrim(numero_de_operacion) <> ''
AND numero_normalizado <> '');
ALTER TABLE pago_informado ADD CONSTRAINT ck_pago_cbu CHECK
(cbu_origen IS NULL OR cbu_origen ~ '^[0-9]{22}$');
ALTER TABLE pago_informado ADD CONSTRAINT uq_pago_comprobante UNIQUE
(administracion_id,complejo_id,comprobante_id);
ALTER TABLE pago_informado ADD CONSTRAINT uq_pago_adm_id UNIQUE (administracion_id,id);
ALTER TABLE pago_informado ADD CONSTRAINT uq_pago_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE pago_informado ADD CONSTRAINT fk_pago_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE pago_informado ADD CONSTRAINT fk_pago_comprobante FOREIGN KEY
(administracion_id,complejo_id,comprobante_id) REFERENCES comprobante_de_pago
(administracion_id,complejo_id,id);
ALTER TABLE pago_informado ADD CONSTRAINT fk_pago_persona FOREIGN KEY
(administracion_id,informado_por) REFERENCES persona (administracion_id,id);
CREATE INDEX ix_pago_numero ON pago_informado
(administracion_id,complejo_id,banco_normalizado,numero_normalizado);
CREATE INDEX ix_pago_edificio ON pago_informado (administracion_id,complejo_id,informado_en);

CREATE TABLE parte_de_pago (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, pago_id UUID NOT NULL, unidad_id UUID NOT NULL,
    importe NUMERIC(14,2) NOT NULL
);
ALTER TABLE parte_de_pago ADD CONSTRAINT ck_parte_importe CHECK (importe > 0);
ALTER TABLE parte_de_pago ADD CONSTRAINT uq_parte_pago_unidad UNIQUE
(administracion_id,pago_id,unidad_id);
ALTER TABLE parte_de_pago ADD CONSTRAINT fk_parte_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE parte_de_pago ADD CONSTRAINT fk_parte_pago FOREIGN KEY
(administracion_id,complejo_id,pago_id) REFERENCES pago_informado
(administracion_id,complejo_id,id);
ALTER TABLE parte_de_pago ADD CONSTRAINT fk_parte_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);
CREATE INDEX ix_parte_unidad ON parte_de_pago (administracion_id,unidad_id);

CREATE TABLE evento_de_pago (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    pago_id UUID NOT NULL, tipo TEXT NOT NULL, motivo TEXT, registrado_por UUID NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE evento_de_pago ADD CONSTRAINT ck_evento_pago_tipo CHECK
(tipo IN ('confirmado','rechazado','revertido','reimputado'));
ALTER TABLE evento_de_pago ADD CONSTRAINT ck_evento_pago_motivo CHECK (
    (tipo = 'confirmado' AND (motivo IS NULL OR char_length(motivo) BETWEEN 1 AND 500))
    OR (tipo <> 'confirmado' AND motivo IS NOT NULL AND char_length(motivo) BETWEEN 1 AND 500
        AND btrim(motivo) <> ''));
ALTER TABLE evento_de_pago ADD CONSTRAINT fk_evento_pago FOREIGN KEY
(administracion_id,pago_id) REFERENCES pago_informado (administracion_id,id);
ALTER TABLE evento_de_pago ADD CONSTRAINT fk_evento_pago_persona FOREIGN KEY
(administracion_id,registrado_por) REFERENCES persona (administracion_id,id);
CREATE UNIQUE INDEX uq_evento_pago_resolucion ON evento_de_pago (administracion_id,pago_id)
WHERE tipo IN ('confirmado','rechazado');
CREATE UNIQUE INDEX uq_evento_pago_revertido ON evento_de_pago (administracion_id,pago_id)
WHERE tipo = 'revertido';
CREATE INDEX ix_evento_pago ON evento_de_pago (administracion_id,pago_id,registrado_en);

CREATE TABLE movimiento_de_pago (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    pago_id UUID NOT NULL, movimiento_id UUID NOT NULL, papel TEXT NOT NULL
);
ALTER TABLE movimiento_de_pago ADD CONSTRAINT ck_movimiento_de_pago_papel CHECK
(papel IN ('pago','ajuste_de_interes','reversion_de_pago','interes_por_reversion','reimputacion'));
ALTER TABLE movimiento_de_pago ADD CONSTRAINT uq_movimiento_de_pago UNIQUE
(administracion_id,pago_id,movimiento_id);
ALTER TABLE movimiento_de_pago ADD CONSTRAINT fk_movimiento_de_pago_pago FOREIGN KEY
(administracion_id,pago_id) REFERENCES pago_informado (administracion_id,id);
ALTER TABLE movimiento_de_pago ADD CONSTRAINT fk_movimiento_de_pago_movimiento FOREIGN KEY
(administracion_id,movimiento_id) REFERENCES movimiento (administracion_id,id);

CREATE TABLE cbu_de_unidad (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, unidad_id UUID NOT NULL, cbu TEXT NOT NULL, pago_id UUID NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE cbu_de_unidad ADD CONSTRAINT ck_cbu_de_unidad CHECK (cbu ~ '^[0-9]{22}$');
ALTER TABLE cbu_de_unidad ADD CONSTRAINT uq_cbu_de_unidad UNIQUE
(administracion_id,unidad_id,cbu,pago_id);
ALTER TABLE cbu_de_unidad ADD CONSTRAINT fk_cbu_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE cbu_de_unidad ADD CONSTRAINT fk_cbu_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);
ALTER TABLE cbu_de_unidad ADD CONSTRAINT fk_cbu_pago FOREIGN KEY
(administracion_id,complejo_id,pago_id) REFERENCES pago_informado
(administracion_id,complejo_id,id);

CREATE FUNCTION fn_pago_informado_numero_unico() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(
        'pago|' || NEW.administracion_id::text || '|' || NEW.complejo_id::text || '|'
        || NEW.banco_normalizado || '|' || NEW.numero_normalizado, 0));
    IF EXISTS (
        SELECT 1 FROM public.pago_informado p
        WHERE p.administracion_id = NEW.administracion_id AND p.complejo_id = NEW.complejo_id
          AND p.banco_normalizado = NEW.banco_normalizado
          AND p.numero_normalizado = NEW.numero_normalizado
          AND NOT EXISTS (SELECT 1 FROM public.evento_de_pago e
                          WHERE e.administracion_id = p.administracion_id AND e.pago_id = p.id
                            AND e.tipo = 'rechazado')
    ) THEN
        RAISE EXCEPTION 'el numero de operacion ya esta informado en el edificio'
            USING ERRCODE = 'unique_violation', CONSTRAINT = 'uq_pago_numero_por_edificio';
    END IF;
    RETURN NEW;
END; $$;
CREATE TRIGGER trg_pago_informado_numero_unico BEFORE INSERT ON pago_informado
FOR EACH ROW EXECUTE FUNCTION fn_pago_informado_numero_unico();
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
    for tabla in _TABLAS:
        op.execute(_proteger(tabla))
        aislar_por_administracion(tabla)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    for tabla in reversed(_TABLAS):
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
    hay_filas = " OR ".join(f'EXISTS (SELECT 1 FROM "{tabla}")' for tabla in _TABLAS)  # noqa: S608
    op.execute(
        f"""DO $$ BEGIN
        IF {hay_filas} THEN
            RAISE EXCEPTION 'hay pagos informados: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    for tabla in reversed(_TABLAS):
        op.execute(f'DROP TABLE "{tabla}"')
        op.execute(f'DROP FUNCTION "fn_{tabla}_bloqueada"()')
    op.execute("DROP FUNCTION fn_pago_informado_numero_unico()")
