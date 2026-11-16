"""Tablas de la liquidación emitida y la acción `ver_liquidaciones` (liquidacion-y-emision, H-013,
design E2, E14).

Todo lo que se usó al emitir queda guardado y nada de lo que cambie después lo altera: la
liquidación (con su huella, la versión de configuración, el porcentaje de fondo, el vencimiento y,
si se corrió, el original con su motivo), las categorías de cada bloque con **su nombre al emitir**,
los grupos con la composición y el coeficiente efectivo, una línea por unidad (con la foto del saldo
anterior) y las alertas aceptadas. Las seis son de sólo agregar, con el patrón del libro (`0035`,
`0039`): tres triggers cada una y RLS forzada por administración. Sin `ALTER` sobre ninguna tabla
protegida existente. No importa `Accion`: el vocabulario de una migración no cambia con el
código vivo.

Revision ID: 0041
Revises: 0040
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ACCION = "ver_liquidaciones"
#: Del hijo al padre al subir; al bajar se borran al revés.
_TABLAS = (
    "liquidacion",
    "categoria_de_liquidacion",
    "grupo_de_liquidacion",
    "composicion_de_grupo",
    "linea_de_liquidacion",
    "alerta_aceptada",
)

_DDL = """
CREATE TABLE liquidacion (
    id UUID PRIMARY KEY, administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
    emision_id UUID NOT NULL, periodo DATE NOT NULL, huella TEXT NOT NULL,
    version_de_configuracion_id UUID NOT NULL, porcentaje_fondo NUMERIC(5,2) NOT NULL,
    vencimiento DATE NOT NULL, vencimiento_original DATE, motivo_del_vencimiento TEXT,
    total_gastos NUMERIC(14,2) NOT NULL, total_notas_de_credito NUMERIC(14,2) NOT NULL,
    total_fondo_de_reserva NUMERIC(14,2) NOT NULL, total_prorrateado NUMERIC(14,2) NOT NULL,
    total_cargos_particulares NUMERIC(14,2) NOT NULL, total_intereses NUMERIC(14,2) NOT NULL,
    total NUMERIC(14,2) NOT NULL, emitida_por UUID NOT NULL, request_id UUID NOT NULL,
    emitida_en TIMESTAMPTZ NOT NULL
);
ALTER TABLE liquidacion ADD CONSTRAINT ck_liquidacion_periodo CHECK
(periodo = date_trunc('month', periodo)::date);
ALTER TABLE liquidacion ADD CONSTRAINT ck_liquidacion_huella CHECK (char_length(huella) > 0);
ALTER TABLE liquidacion ADD CONSTRAINT ck_liquidacion_vencimiento CHECK (vencimiento >= periodo);
ALTER TABLE liquidacion ADD CONSTRAINT ck_liquidacion_vencimiento_corrido CHECK (
    (vencimiento_original IS NULL AND motivo_del_vencimiento IS NULL)
    OR (vencimiento_original IS NOT NULL AND char_length(motivo_del_vencimiento) BETWEEN 1 AND 500
        AND motivo_del_vencimiento ~ '\\S'));
ALTER TABLE liquidacion ADD CONSTRAINT uq_liquidacion_emision UNIQUE (administracion_id,emision_id);
ALTER TABLE liquidacion ADD CONSTRAINT uq_liquidacion_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE liquidacion ADD CONSTRAINT fk_liquidacion_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE liquidacion ADD CONSTRAINT fk_liquidacion_emision FOREIGN KEY
(administracion_id,complejo_id,periodo,emision_id) REFERENCES emision
(administracion_id,complejo_id,periodo,id);
ALTER TABLE liquidacion ADD CONSTRAINT fk_liquidacion_persona FOREIGN KEY
(administracion_id,emitida_por) REFERENCES persona (administracion_id,id);
CREATE INDEX ix_liquidacion_edificio ON liquidacion (administracion_id,complejo_id,periodo);

CREATE TABLE categoria_de_liquidacion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, liquidacion_id UUID NOT NULL, bloque TEXT NOT NULL,
    orden INTEGER NOT NULL, categoria_id UUID NOT NULL, nombre TEXT NOT NULL,
    importe NUMERIC(14,2) NOT NULL, porcentaje NUMERIC NOT NULL
);
ALTER TABLE categoria_de_liquidacion ADD CONSTRAINT ck_categoria_de_liquidacion_bloque CHECK
(bloque IN ('ordinario','extraordinario'));
ALTER TABLE categoria_de_liquidacion ADD CONSTRAINT uq_categoria_de_liquidacion UNIQUE
(administracion_id,liquidacion_id,bloque,categoria_id);
ALTER TABLE categoria_de_liquidacion ADD CONSTRAINT fk_categoria_de_liquidacion_liquidacion
FOREIGN KEY (administracion_id,complejo_id,liquidacion_id) REFERENCES liquidacion
(administracion_id,complejo_id,id);
ALTER TABLE categoria_de_liquidacion ADD CONSTRAINT fk_categoria_de_liquidacion_categoria
FOREIGN KEY (administracion_id,complejo_id,categoria_id) REFERENCES categoria_de_gasto
(administracion_id,complejo_id,id);

CREATE TABLE grupo_de_liquidacion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, liquidacion_id UUID NOT NULL, orden INTEGER NOT NULL,
    grupo_id UUID NOT NULL, nombre TEXT NOT NULL, metodo TEXT NOT NULL,
    ordinario NUMERIC(14,2) NOT NULL, extraordinario NUMERIC(14,2) NOT NULL
);
ALTER TABLE grupo_de_liquidacion ADD CONSTRAINT uq_grupo_de_liquidacion UNIQUE
(administracion_id,liquidacion_id,grupo_id);
ALTER TABLE grupo_de_liquidacion ADD CONSTRAINT fk_grupo_de_liquidacion_liquidacion
FOREIGN KEY (administracion_id,complejo_id,liquidacion_id) REFERENCES liquidacion
(administracion_id,complejo_id,id);
ALTER TABLE grupo_de_liquidacion ADD CONSTRAINT fk_grupo_de_liquidacion_grupo
FOREIGN KEY (administracion_id,complejo_id,grupo_id) REFERENCES grupo_de_reparto
(administracion_id,complejo_id,id);

CREATE TABLE composicion_de_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, liquidacion_id UUID NOT NULL, grupo_id UUID NOT NULL,
    orden INTEGER NOT NULL, unidad_id UUID NOT NULL, coeficiente NUMERIC(8,6) NOT NULL
);
ALTER TABLE composicion_de_grupo ADD CONSTRAINT uq_composicion_de_grupo UNIQUE
(administracion_id,liquidacion_id,grupo_id,unidad_id);
ALTER TABLE composicion_de_grupo ADD CONSTRAINT fk_composicion_de_grupo_grupo FOREIGN KEY
(administracion_id,liquidacion_id,grupo_id) REFERENCES grupo_de_liquidacion
(administracion_id,liquidacion_id,grupo_id);
ALTER TABLE composicion_de_grupo ADD CONSTRAINT fk_composicion_de_grupo_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);

CREATE TABLE linea_de_liquidacion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, liquidacion_id UUID NOT NULL, orden INTEGER NOT NULL,
    unidad_id UUID NOT NULL, identificador TEXT NOT NULL, ordinaria NUMERIC(14,2) NOT NULL,
    fondo_de_reserva NUMERIC(14,2) NOT NULL, extraordinaria NUMERIC(14,2) NOT NULL,
    intereses NUMERIC(14,2) NOT NULL, total NUMERIC(14,2) NOT NULL, sin_obligacion BOOLEAN NOT NULL,
    saldo_anterior NUMERIC(14,2) NOT NULL, cargos_particulares JSONB NOT NULL,
    por_grupo JSONB NOT NULL
);
ALTER TABLE linea_de_liquidacion ADD CONSTRAINT uq_linea_de_liquidacion UNIQUE
(administracion_id,liquidacion_id,unidad_id);
ALTER TABLE linea_de_liquidacion ADD CONSTRAINT fk_linea_de_liquidacion_liquidacion
FOREIGN KEY (administracion_id,complejo_id,liquidacion_id) REFERENCES liquidacion
(administracion_id,complejo_id,id);
ALTER TABLE linea_de_liquidacion ADD CONSTRAINT fk_linea_de_liquidacion_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);

CREATE TABLE alerta_aceptada (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, liquidacion_id UUID NOT NULL, codigo TEXT NOT NULL,
    mensaje TEXT NOT NULL, detalle JSONB NOT NULL, aceptada_por UUID NOT NULL,
    aceptada_en TIMESTAMPTZ NOT NULL
);
ALTER TABLE alerta_aceptada ADD CONSTRAINT ck_alerta_aceptada_codigo CHECK
(char_length(codigo) > 0);
ALTER TABLE alerta_aceptada ADD CONSTRAINT uq_alerta_aceptada UNIQUE
(administracion_id,liquidacion_id,codigo);
ALTER TABLE alerta_aceptada ADD CONSTRAINT fk_alerta_aceptada_liquidacion FOREIGN KEY
(administracion_id,complejo_id,liquidacion_id) REFERENCES liquidacion
(administracion_id,complejo_id,id);
ALTER TABLE alerta_aceptada ADD CONSTRAINT fk_alerta_aceptada_persona FOREIGN KEY
(administracion_id,aceptada_por) REFERENCES persona (administracion_id,id);
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
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    for tabla in _TABLAS:
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
    for tabla in _TABLAS:
        op.execute(
            f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM "{tabla}") THEN
                RAISE EXCEPTION 'la liquidación tiene filas: la migración no puede bajarse';
            END IF;
        END $$"""  # noqa: S608 - los nombres son literales de este archivo
        )
    for tabla in reversed(_TABLAS):
        op.execute(f'DROP TABLE "{tabla}"')
        op.execute(f'DROP FUNCTION "fn_{tabla}_bloqueada"()')
    acciones = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(acciones.delete().where(acciones.c.nombre == _ACCION))
