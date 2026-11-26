"""El prorrateo por días de la expensa del mes del cambio (cambio-de-titular, H-032, D-168.5, R32).

Dos tablas de sólo agregar (D-115): tres triggers cada una y RLS forzada por administración, y a
cargo del rol de arranque cuando corre `roles despues`. Ninguna altera una tabla protegida
existente.

- `prorrateo_de_cambio`: lo que pidió un cambio con `expensa_del_mes = 'prorrateo'`: el período
  (primer día del mes de la fecha), los días del vendedor y los del mes. **Único por unidad y
  período** (`uq_prorrateo_unidad_periodo`): un segundo prorrateo del mismo mes lo frena la base.
  Mientras no tenga fila en `prorrateo_aplicado` está pendiente.
- `prorrateo_aplicado`: una fila por prorrateo que ya movió el libro (al registrar si el período
  ya estaba emitido, o al emitirlo), con lo efectivamente trasladado (`parte_del_vendedor`, cero
  si el cambio fue el día 1 o la unidad ya había pagado esa parte). Como la tabla no admite
  `UPDATE`, "pendiente" es la ausencia de esta fila: el estado nunca se reescribe.

Sin `ALTER` sobre ninguna tabla protegida; no importa `Accion` (L-089).

Revision ID: 0052
Revises: 0051
"""

from collections.abc import Sequence

from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLAS = ("prorrateo_de_cambio", "prorrateo_aplicado")

_DDL = r"""
CREATE TABLE prorrateo_de_cambio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, cambio_id UUID NOT NULL, unidad_id UUID NOT NULL,
    periodo DATE NOT NULL, dias_del_vendedor INTEGER NOT NULL, dias_del_mes INTEGER NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT ck_prorrateo_periodo CHECK
(periodo IS NOT NULL AND EXTRACT(DAY FROM periodo) = 1);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT ck_prorrateo_dias CHECK
(dias_del_mes IS NOT NULL AND dias_del_vendedor IS NOT NULL AND dias_del_mes BETWEEN 28 AND 31
 AND dias_del_vendedor >= 0 AND dias_del_vendedor < dias_del_mes);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT uq_prorrateo_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT uq_prorrateo_cambio UNIQUE
(administracion_id,cambio_id);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT uq_prorrateo_unidad_periodo UNIQUE
(administracion_id,unidad_id,periodo);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT fk_prorrateo_cambio FOREIGN KEY
(administracion_id,complejo_id,cambio_id) REFERENCES cambio_de_titular
(administracion_id,complejo_id,id);
ALTER TABLE prorrateo_de_cambio ADD CONSTRAINT fk_prorrateo_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);
CREATE INDEX ix_prorrateo_periodo ON prorrateo_de_cambio (administracion_id,complejo_id,periodo);

CREATE TABLE prorrateo_aplicado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, prorrateo_id UUID NOT NULL,
    parte_del_vendedor NUMERIC(14,2) NOT NULL,
    aplicado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE prorrateo_aplicado ADD CONSTRAINT ck_prorrateo_aplicado_parte CHECK
(parte_del_vendedor IS NOT NULL AND parte_del_vendedor >= 0);
ALTER TABLE prorrateo_aplicado ADD CONSTRAINT uq_prorrateo_aplicado UNIQUE
(administracion_id,prorrateo_id);
ALTER TABLE prorrateo_aplicado ADD CONSTRAINT fk_prorrateo_aplicado FOREIGN KEY
(administracion_id,complejo_id,prorrateo_id) REFERENCES prorrateo_de_cambio
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
    for tabla in _TABLAS:
        op.execute(_proteger(tabla))
        aislar_por_administracion(tabla)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    for tabla in reversed(_TABLAS):
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM prorrateo_de_cambio) THEN
            RAISE EXCEPTION 'hay prorrateos de cambios de titular: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    for tabla in reversed(_TABLAS):
        op.execute(f'DROP TABLE "{tabla}"')
        op.execute(f'DROP FUNCTION "fn_{tabla}_bloqueada"()')
