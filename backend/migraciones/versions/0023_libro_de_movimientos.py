"""Tablas del libro (E1 a E16): nueva estructura transaccional, sin datos previos.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLAS = ("cuenta", "emision", "evento_de_emision", "obligacion", "movimiento", "imputacion")


def upgrade() -> None:
    op.execute("""
        CREATE TABLE cuenta (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            unidad_id UUID, persona_id UUID, creada_en TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE candado_de_cuenta (cuenta_id UUID PRIMARY KEY, administracion_id UUID NOT
        NULL);
        CREATE TABLE emision (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            periodo DATE NOT NULL, intento INTEGER NOT NULL, registrada_por UUID NOT NULL,
            request_id UUID NOT NULL, registrada_en TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE evento_de_emision (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            emision_id UUID NOT NULL, tipo TEXT NOT NULL, motivo TEXT NOT NULL,
            persona_id UUID NOT NULL, request_id UUID NOT NULL, registrado_en TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE tipo_de_movimiento (tipo TEXT NOT NULL, sentido TEXT NOT NULL,
            PRIMARY KEY (tipo,sentido));
        CREATE TABLE obligacion (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            cuenta_id UUID NOT NULL, emision_id UUID, operacion_id UUID, periodo DATE NOT NULL,
            vencimiento DATE NOT NULL, ordinaria NUMERIC(14,2) NOT NULL,
            fondo_de_reserva NUMERIC(14,2) NOT NULL, extraordinaria NUMERIC(14,2) NOT NULL,
            registrada_en TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE movimiento (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            cuenta_id UUID NOT NULL, tipo TEXT NOT NULL, sentido TEXT NOT NULL,
            importe NUMERIC(14,2) NOT NULL, fecha_valor DATE NOT NULL,
        registrado_por UUID NOT NULL, request_id UUID NOT NULL, registrado_en TIMESTAMPTZ NOT NULL,
            operacion_id UUID, emision_id UUID, obligacion_id UUID, componente TEXT, corte DATE,
            corrige_a UUID, tipo_corregido TEXT, enlazado_a UUID, motivo TEXT
        );
        CREATE TABLE imputacion (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
        cuenta_id UUID NOT NULL, movimiento_id UUID NOT NULL, sentido_del_movimiento TEXT NOT NULL,
            obligacion_id UUID NOT NULL, componente TEXT NOT NULL, importe NUMERIC(14,2) NOT NULL,
            corrida_id UUID NOT NULL, orden BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
            registrada_en TIMESTAMPTZ NOT NULL
        );
    """)
    # Tablas nuevas y vacías: constraints e índices transaccionales antes de publicarlas.
    # ix_obligacion_cuenta_periodo: lectura por administración/cuenta, ordenada por período.
    # ix_movimiento_cuenta/ix_imputacion_cuenta: lectura por administración y cuenta.
    op.execute("""
        ALTER TABLE cuenta ADD CONSTRAINT ck_cuenta_duenio CHECK
        (num_nonnulls(unidad_id,persona_id)=1);
        ALTER TABLE emision ADD CONSTRAINT ck_emision_periodo CHECK (extract(day FROM periodo)=1);
        ALTER TABLE emision ADD CONSTRAINT ck_emision_intento CHECK (intento>=1);
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_tipo CHECK (tipo='anulada');
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_motivo CHECK (length(motivo)
        BETWEEN 1 AND 500 AND btrim(motivo)<>'');
        ALTER TABLE obligacion ADD CONSTRAINT ck_obligacion_origen CHECK
        (num_nonnulls(emision_id,operacion_id)=1);
        ALTER TABLE obligacion ADD CONSTRAINT ck_obligacion_periodo CHECK (extract(day FROM
        periodo)=1);
        ALTER TABLE obligacion ADD CONSTRAINT ck_obligacion_importes CHECK (ordinaria>=0 AND
        fondo_de_reserva>=0 AND extraordinaria>=0 AND ordinaria+fondo_de_reserva+extraordinaria>0);
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_importe CHECK (importe>0);
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_componente CHECK (componente IN
        ('interes','ordinaria','fondo_de_reserva','extraordinaria'));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_interes CHECK (tipo<>'interes' OR
        (obligacion_id IS NOT NULL AND componente IS NOT NULL AND componente='interes' AND corte
        IS NOT NULL));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_destino_interes CHECK (tipo NOT IN
        ('condonacion','ajuste_de_interes') OR (obligacion_id IS NOT NULL AND componente IS NOT
        NULL AND componente='interes'));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_bonificacion CHECK (tipo<>'bonificacion' OR
        (obligacion_id IS NOT NULL AND componente IS NOT NULL AND componente='ordinaria'));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_debito_destino CHECK (sentido<>'debito' OR
        corrige_a IS NOT NULL OR (obligacion_id IS NOT NULL AND componente IS NOT NULL));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_operacion CHECK (tipo='interes' OR
        operacion_id IS NOT NULL);
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_motivo CHECK (tipo<>'correccion' OR (motivo
        IS NOT NULL AND length(motivo) BETWEEN 1 AND 500 AND btrim(motivo)<>''));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_correccion_debito CHECK (tipo<>'correccion'
        OR sentido<>'debito' OR corrige_a IS NOT NULL);
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_correccion_credito CHECK (tipo<>'correccion'
        OR corrige_a IS NOT NULL OR obligacion_id IS NOT NULL);
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_corrige_tipo CHECK (corrige_a IS NULL OR
        tipo='correccion');
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_corrige_par CHECK
        (num_nulls(corrige_a,tipo_corregido) IN (0,2));
        ALTER TABLE imputacion ADD CONSTRAINT ck_imputacion_importe CHECK (importe>0);
        ALTER TABLE imputacion ADD CONSTRAINT ck_imputacion_componente CHECK (componente IN
        ('interes','ordinaria','fondo_de_reserva','extraordinaria'));
        ALTER TABLE imputacion ADD CONSTRAINT ck_imputacion_sentido CHECK
        (sentido_del_movimiento='credito');
        ALTER TABLE tipo_de_movimiento ADD CONSTRAINT ck_tipo_no_vacio CHECK (btrim(tipo)<>'');
        ALTER TABLE tipo_de_movimiento ADD CONSTRAINT ck_tipo_sentido CHECK (sentido IN
        ('debito','credito'));
        ALTER TABLE cuenta ADD CONSTRAINT uq_cuenta_adm_id UNIQUE (administracion_id,id);
        ALTER TABLE cuenta ADD CONSTRAINT uq_cuenta_edificio_id UNIQUE
        (administracion_id,complejo_id,id);
        ALTER TABLE emision ADD CONSTRAINT uq_emision_edificio_id UNIQUE
        (administracion_id,complejo_id,id);
        ALTER TABLE emision ADD CONSTRAINT uq_emision_periodo_id UNIQUE
        (administracion_id,complejo_id,periodo,id);
        ALTER TABLE emision ADD CONSTRAINT uq_emision_intento UNIQUE
        (administracion_id,complejo_id,periodo,intento);
        ALTER TABLE evento_de_emision ADD CONSTRAINT uq_evento_emision_tipo UNIQUE
        (administracion_id,emision_id,tipo);
        ALTER TABLE obligacion ADD CONSTRAINT uq_obligacion_cuenta_id UNIQUE
        (administracion_id,complejo_id,cuenta_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT uq_mov_adm_id UNIQUE (administracion_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT uq_mov_sentido UNIQUE
        (administracion_id,complejo_id,cuenta_id,id,sentido);
        ALTER TABLE movimiento ADD CONSTRAINT uq_mov_correccion UNIQUE
        (administracion_id,complejo_id,cuenta_id,id,tipo,importe);
        ALTER TABLE cuenta ADD CONSTRAINT fk_cuenta_admin FOREIGN KEY (administracion_id)
        REFERENCES administracion (id);
        ALTER TABLE cuenta ADD CONSTRAINT fk_cuenta_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE cuenta ADD CONSTRAINT fk_cuenta_unidad FOREIGN KEY
        (administracion_id,complejo_id,unidad_id) REFERENCES unidad
        (administracion_id,complejo_id,id);
        ALTER TABLE cuenta ADD CONSTRAINT fk_cuenta_persona FOREIGN KEY
        (administracion_id,persona_id) REFERENCES persona (administracion_id,id);
        ALTER TABLE candado_de_cuenta ADD CONSTRAINT fk_candado_cuenta FOREIGN KEY
        (administracion_id,cuenta_id) REFERENCES cuenta (administracion_id,id);
        ALTER TABLE emision ADD CONSTRAINT fk_emision_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE emision ADD CONSTRAINT fk_emision_persona FOREIGN KEY
        (administracion_id,registrada_por) REFERENCES persona (administracion_id,id);
        ALTER TABLE evento_de_emision ADD CONSTRAINT fk_evento_emision FOREIGN KEY
        (administracion_id,complejo_id,emision_id) REFERENCES emision
        (administracion_id,complejo_id,id);
        ALTER TABLE evento_de_emision ADD CONSTRAINT fk_evento_persona FOREIGN KEY
        (administracion_id,persona_id) REFERENCES persona (administracion_id,id);
        ALTER TABLE obligacion ADD CONSTRAINT fk_obligacion_cuenta FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id) REFERENCES cuenta
        (administracion_id,complejo_id,id);
        ALTER TABLE obligacion ADD CONSTRAINT fk_obligacion_emision FOREIGN KEY
        (administracion_id,complejo_id,periodo,emision_id) REFERENCES emision
        (administracion_id,complejo_id,periodo,id);
        ALTER TABLE evento_de_emision ADD CONSTRAINT fk_evento_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE obligacion ADD CONSTRAINT fk_obligacion_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE imputacion ADD CONSTRAINT fk_imputacion_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_tipo_sentido FOREIGN KEY (tipo,sentido)
        REFERENCES tipo_de_movimiento (tipo,sentido);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_cuenta FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id) REFERENCES cuenta
        (administracion_id,complejo_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_obligacion FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,obligacion_id) REFERENCES obligacion
        (administracion_id,complejo_id,cuenta_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_emision FOREIGN KEY
        (administracion_id,complejo_id,emision_id) REFERENCES emision
        (administracion_id,complejo_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_persona FOREIGN KEY
        (administracion_id,registrado_por) REFERENCES persona (administracion_id,id);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_corrige FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,corrige_a,tipo_corregido,importe) REFERENCES
        movimiento (administracion_id,complejo_id,cuenta_id,id,tipo,importe);
        ALTER TABLE movimiento ADD CONSTRAINT fk_mov_enlazado FOREIGN KEY
        (administracion_id,enlazado_a) REFERENCES movimiento (administracion_id,id);
        ALTER TABLE imputacion ADD CONSTRAINT fk_imputacion_movimiento FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,movimiento_id,sentido_del_movimiento) REFERENCES
        movimiento (administracion_id,complejo_id,cuenta_id,id,sentido);
        ALTER TABLE imputacion ADD CONSTRAINT fk_imputacion_obligacion FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,obligacion_id) REFERENCES obligacion
        (administracion_id,complejo_id,cuenta_id,id);
        CREATE UNIQUE INDEX uq_cuenta_unidad ON cuenta (administracion_id,unidad_id) WHERE
        unidad_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_cuenta_persona ON cuenta (administracion_id,complejo_id,persona_id)
        WHERE persona_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_obligacion_emision ON obligacion
        (administracion_id,emision_id,cuenta_id) WHERE emision_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_obligacion_operacion ON obligacion
        (administracion_id,operacion_id,cuenta_id,periodo) WHERE operacion_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_mov_operacion ON movimiento (administracion_id,operacion_id) WHERE
        operacion_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_mov_corrige_a ON movimiento (administracion_id,corrige_a) WHERE
        corrige_a IS NOT NULL;
        CREATE UNIQUE INDEX uq_mov_interes ON movimiento (administracion_id,obligacion_id,corte)
        WHERE tipo='interes';
        CREATE INDEX ix_obligacion_cuenta_periodo ON obligacion
        (administracion_id,cuenta_id,periodo);
        CREATE INDEX ix_movimiento_cuenta ON movimiento (administracion_id,cuenta_id);
        CREATE INDEX ix_imputacion_cuenta ON imputacion (administracion_id,cuenta_id);
    """)
    op.execute("""
        INSERT INTO tipo_de_movimiento (tipo,sentido) VALUES
        ('interes','debito'), ('pago','credito'), ('correccion','debito'), ('correccion','credito'),
        ('condonacion','credito'), ('ajuste_de_interes','credito'), ('bonificacion','credito'),
        ('baja_de_deuda','credito'), ('saldo_inicial','credito'), ('reversion_de_pago','debito'),
        ('reimputacion','debito'), ('reimputacion','credito'),
        ('traslado','debito'), ('traslado','credito');
        REVOKE INSERT, UPDATE, DELETE ON tipo_de_movimiento FROM proptech_app;
        GRANT SELECT ON tipo_de_movimiento TO proptech_app;
    """)
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
    for tabla in _TABLAS:
        aislar_por_administracion(tabla)
    aislar_por_administracion("candado_de_cuenta", permisos="SELECT, INSERT, UPDATE")
    # Después del GRANT de aislar: los DEFAULT PRIVILEGES de `roles antes` le dieron DELETE (F1-01).
    op.execute("REVOKE DELETE ON candado_de_cuenta FROM proptech_app")


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir que es reversible.
    # Cada ALTER toma un bloqueo exclusivo, conservado hasta finalizar la migración.
    for tabla in _TABLAS:
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
        # tabla proviene de _TABLAS, una tupla literal de esta migración.
        op.execute(
            f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM "{tabla}") THEN
                RAISE EXCEPTION '{tabla} tiene filas: el libro no puede bajarse';
            END IF;
        END $$"""  # noqa: S608
        )
    for tabla in (
        "imputacion",
        "movimiento",
        "obligacion",
        "evento_de_emision",
        "emision",
        "candado_de_cuenta",
        "cuenta",
        "tipo_de_movimiento",
    ):
        op.execute(f'DROP TABLE "{tabla}"')
    for tabla in _TABLAS:
        op.execute(f"DROP FUNCTION fn_{tabla}_bloqueada()")
