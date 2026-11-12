"""Importación desde Excel: la tabla `importacion` y el vocabulario de `importar` (design D5, D10).

Una fila por subida aceptada. La app la cambia de estado (`borrador` → `descartada` o
`confirmada`): no es de sólo agregar y no entra en `TABLAS_DE_SOLO_AGREGAR`. Las tablas del
borrador de saldos (H-008) cuelgan de `(administracion_id, complejo_id, id)` y van en la `0037`.

Revision ID: 0036
Revises: 0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ACCION = "importar_padron_y_saldos"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE importacion (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            administracion_id UUID NOT NULL, complejo_id UUID NOT NULL,
            archivo TEXT NOT NULL, huella TEXT NOT NULL, fecha_de_migracion DATE NOT NULL,
            estado TEXT NOT NULL DEFAULT 'borrador',
            creada_por UUID NOT NULL, creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        ALTER TABLE importacion ADD CONSTRAINT ck_importacion_archivo CHECK
            (length(archivo) BETWEEN 1 AND 255);
        ALTER TABLE importacion ADD CONSTRAINT ck_importacion_huella CHECK
            (huella ~ '^[0-9a-f]{64}$');
        ALTER TABLE importacion ADD CONSTRAINT ck_importacion_estado CHECK
            (estado IN ('borrador', 'descartada', 'confirmada'));
        ALTER TABLE importacion ADD CONSTRAINT uq_importacion_edificio_id UNIQUE
            (administracion_id, complejo_id, id);
        ALTER TABLE importacion ADD CONSTRAINT fk_importacion_complejo FOREIGN KEY
            (administracion_id, complejo_id) REFERENCES complejo (administracion_id, id);
        ALTER TABLE importacion ADD CONSTRAINT fk_importacion_persona FOREIGN KEY
            (administracion_id, creada_por) REFERENCES persona (administracion_id, id);
        CREATE UNIQUE INDEX uq_importacion_un_borrador ON importacion
            (administracion_id, complejo_id) WHERE estado = 'borrador';
        CREATE UNIQUE INDEX uq_importacion_huella ON importacion
            (administracion_id, complejo_id, huella) WHERE estado <> 'descartada';
    """)
    aislar_por_administracion("importacion")
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # El dueño sin tenant tiene que ver TODAS las filas antes de decidir (patrón de `0032`).
    op.execute('ALTER TABLE "importacion" NO FORCE ROW LEVEL SECURITY')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM "importacion") THEN
            RAISE EXCEPTION 'importacion tiene filas: la migración no puede bajarse';
        END IF;
    END $$""")
    op.execute('DROP TABLE "importacion"')
    # La FK de `auditoria` impide retirar el vocabulario usado (23503), como en la `0024`.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre == _ACCION))
