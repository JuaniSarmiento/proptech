"""Vocabulario de auditoría `editar_edificio` (3c, tarea 3.7) y
`grupo_de_reparto.activo` (3c, tarea 4.3): sin backfill (D3) — nace
`NOT NULL DEFAULT true`, así que todo grupo existente queda activo sin
tocar sus filas. El trigger de `0011` (protección de "Generales") se
amplía para que tampoco admita desactivar "Generales", ni por la API ni
por SQL — mismo criterio que `es_generales`/`metodo`/`modo_de_coeficientes`.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_EVENTOS = ("editar_edificio",)

#: Versión real tras `0015` (RF-D-1, 19/10/2026) — nunca la de `0011` sola:
#: ya suma `complejo_id`/`administracion_id` a la comparación. El downgrade
#: de ESTA migración restaura exactamente esto, no la versión de `0011`.
_FUNCION_SIN_ACTIVO = """
        CREATE OR REPLACE FUNCTION fn_grupo_generales_protegido() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.es_generales THEN
                    RAISE EXCEPTION 'Generales no admite DELETE';
                END IF;
                RETURN OLD;
            END IF;
            IF OLD.es_generales AND (
                NEW.es_generales IS DISTINCT FROM OLD.es_generales
                OR NEW.metodo IS DISTINCT FROM OLD.metodo
                OR NEW.modo_de_coeficientes IS DISTINCT FROM OLD.modo_de_coeficientes
                OR NEW.complejo_id IS DISTINCT FROM OLD.complejo_id
                OR NEW.administracion_id IS DISTINCT FROM OLD.administracion_id
            ) THEN
                RAISE EXCEPTION
                    'Generales no admite cambiar es_generales, metodo, '
                    'modo_de_coeficientes, complejo_id ni administracion_id';
            END IF;
            RETURN NEW;
        END;
        $$
    """

_FUNCION_AMPLIADA = """
    CREATE OR REPLACE FUNCTION fn_grupo_generales_protegido() RETURNS trigger
    LANGUAGE plpgsql SET search_path = '' AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            IF OLD.es_generales THEN
                RAISE EXCEPTION 'Generales no admite DELETE';
            END IF;
            RETURN OLD;
        END IF;
        IF OLD.es_generales AND (
            NEW.es_generales IS DISTINCT FROM OLD.es_generales
            OR NEW.metodo IS DISTINCT FROM OLD.metodo
            OR NEW.modo_de_coeficientes IS DISTINCT FROM OLD.modo_de_coeficientes
            OR NEW.complejo_id IS DISTINCT FROM OLD.complejo_id
            OR NEW.administracion_id IS DISTINCT FROM OLD.administracion_id
            OR NEW.activo IS DISTINCT FROM OLD.activo
        ) THEN
            RAISE EXCEPTION
                'Generales no admite cambiar es_generales, metodo, '
                'modo_de_coeficientes, complejo_id, administracion_id ni activo';
        END IF;
        RETURN NEW;
    END;
    $$
"""


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )
    op.add_column(
        "grupo_de_reparto",
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(_FUNCION_AMPLIADA)


def downgrade() -> None:
    op.execute(_FUNCION_SIN_ACTIVO)
    op.drop_column("grupo_de_reparto", "activo")
    # La FK 23503 preserva todo evento utilizado: punto de no retorno firmado.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
