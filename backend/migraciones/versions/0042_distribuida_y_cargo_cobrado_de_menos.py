"""El evento `distribuida` y el cargo cobrado de menos (liquidacion-y-emision, H-014, design E9, E11).

1. `evento_de_emision` admite `tipo = 'distribuida'`, una por emisión (E9), con su `origen`
   (`manual`, `email` o `portal`). Una distribuida no lleva motivo, y la persona sólo es obligatoria
   para la distribución manual (el portal y el email pueden no tener una). Una anulada sigue
   exactamente como era. Un índice parcial único deja a lo sumo un cierre por emisión: nunca una
   emisión anulada **y** distribuida, ni por una carrera que se saltee el candado del período.
2. `cargo_cobrado_de_menos` (E11): el motivo, la obligación de origen, la obligación nueva (sin
   emisión, con su `operacion_id`), quién y cuándo. De sólo agregar, con el patrón del libro
   (`0035`, `0039`) y RLS forzada por administración.

Esta migración hace `ALTER` sobre una tabla protegida (`evento_de_emision`): lo declara en
`PRESTA_PROPIEDAD` y `roles antes` se la presta al migrador sólo mientras esta migración está
pendiente (D-115.3); `roles despues` la devuelve y la verifica. No importa `Accion`: el vocabulario
de una migración no cambia con el código vivo (no hay acciones nuevas).

Revision ID: 0042
Revises: 0041
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

#: Las tablas protegidas que esta migración altera (D-115.3): `roles antes` las presta.
PRESTA_PROPIEDAD: tuple[str, ...] = ("evento_de_emision",)

_TABLA = "cargo_cobrado_de_menos"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE evento_de_emision ADD COLUMN origen TEXT;
        ALTER TABLE evento_de_emision ALTER COLUMN motivo DROP NOT NULL;
        ALTER TABLE evento_de_emision ALTER COLUMN persona_id DROP NOT NULL;
        ALTER TABLE evento_de_emision DROP CONSTRAINT ck_evento_tipo;
        ALTER TABLE evento_de_emision DROP CONSTRAINT ck_evento_motivo;
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_tipo CHECK
        (tipo IN ('anulada','distribuida'));
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_motivo CHECK
        (motivo IS NULL OR (length(motivo) BETWEEN 1 AND 500 AND btrim(motivo)<>''));
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_forma CHECK (
            (tipo='anulada' AND origen IS NULL AND motivo IS NOT NULL AND persona_id IS NOT NULL)
            OR (tipo='distribuida' AND motivo IS NULL AND (
                (origen='manual' AND persona_id IS NOT NULL) OR origen IN ('email','portal'))));
        CREATE UNIQUE INDEX uq_evento_emision_cierre ON evento_de_emision
        (administracion_id,emision_id) WHERE tipo IN ('anulada','distribuida');
    """)
    op.execute("""
        CREATE TABLE cargo_cobrado_de_menos (
            id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            cuenta_id UUID NOT NULL, obligacion_id UUID NOT NULL, obligacion_origen_id UUID NOT NULL,
            operacion_id UUID NOT NULL, motivo TEXT NOT NULL, registrado_por UUID NOT NULL,
            request_id UUID NOT NULL, registrado_en TIMESTAMPTZ NOT NULL
        );
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT ck_cargo_motivo CHECK
        (char_length(motivo) BETWEEN 1 AND 500 AND motivo ~ '\\S');
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT uq_cargo_operacion UNIQUE
        (administracion_id,operacion_id);
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT uq_cargo_obligacion UNIQUE
        (administracion_id,obligacion_id);
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT fk_cargo_complejo FOREIGN KEY
        (administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT fk_cargo_obligacion FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,obligacion_id) REFERENCES obligacion
        (administracion_id,complejo_id,cuenta_id,id);
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT fk_cargo_origen FOREIGN KEY
        (administracion_id,complejo_id,cuenta_id,obligacion_origen_id) REFERENCES obligacion
        (administracion_id,complejo_id,cuenta_id,id);
        ALTER TABLE cargo_cobrado_de_menos ADD CONSTRAINT fk_cargo_persona FOREIGN KEY
        (administracion_id,registrado_por) REFERENCES persona (administracion_id,id);
        CREATE INDEX ix_cargo_origen ON cargo_cobrado_de_menos
        (administracion_id,obligacion_origen_id);
        CREATE FUNCTION fn_cargo_cobrado_de_menos_bloqueada() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'cargo_cobrado_de_menos no admite %', TG_OP;
        END; $$;
        CREATE TRIGGER trg_cargo_cobrado_de_menos_sin_update_delete BEFORE UPDATE OR DELETE ON
        cargo_cobrado_de_menos FOR EACH ROW EXECUTE FUNCTION fn_cargo_cobrado_de_menos_bloqueada();
        CREATE TRIGGER trg_cargo_cobrado_de_menos_sin_truncate BEFORE TRUNCATE ON
        cargo_cobrado_de_menos FOR EACH STATEMENT EXECUTE FUNCTION
        fn_cargo_cobrado_de_menos_bloqueada();
        CREATE TRIGGER trg_cargo_cobrado_de_menos_sin_update_delete_por_sentencia BEFORE UPDATE OR
        DELETE ON cargo_cobrado_de_menos FOR EACH STATEMENT EXECUTE FUNCTION
        fn_cargo_cobrado_de_menos_bloqueada();
    """)
    aislar_por_administracion(_TABLA)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute(f'ALTER TABLE "{_TABLA}" NO FORCE ROW LEVEL SECURITY')
    op.execute("ALTER TABLE evento_de_emision NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "cargo_cobrado_de_menos") THEN
            RAISE EXCEPTION 'hay cargos cobrados de menos: la migración no puede bajarse';
        END IF;
        IF EXISTS (SELECT 1 FROM "evento_de_emision" WHERE tipo = 'distribuida') THEN
            RAISE EXCEPTION 'hay liquidaciones distribuidas: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute(f'DROP TABLE "{_TABLA}"')
    op.execute("DROP FUNCTION fn_cargo_cobrado_de_menos_bloqueada()")
    op.execute("""
        DROP INDEX uq_evento_emision_cierre;
        ALTER TABLE evento_de_emision DROP CONSTRAINT ck_evento_forma;
        ALTER TABLE evento_de_emision DROP CONSTRAINT ck_evento_motivo;
        ALTER TABLE evento_de_emision DROP CONSTRAINT ck_evento_tipo;
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_tipo CHECK (tipo='anulada');
        ALTER TABLE evento_de_emision ADD CONSTRAINT ck_evento_motivo CHECK (length(motivo)
        BETWEEN 1 AND 500 AND btrim(motivo)<>'');
        ALTER TABLE evento_de_emision ALTER COLUMN persona_id SET NOT NULL;
        ALTER TABLE evento_de_emision ALTER COLUMN motivo SET NOT NULL;
        ALTER TABLE evento_de_emision DROP COLUMN origen;
        ALTER TABLE evento_de_emision FORCE ROW LEVEL SECURITY;
    """)
