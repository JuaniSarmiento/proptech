""" "Generales" tampoco se muda de edificio, ni por SQL (3a, RF-D-1).

Revisión final del cambio `configuracion-del-edificio` (DBA, 19/10/2026).
El trigger de 0011 (`fn_grupo_generales_protegido`) sólo mira
`es_generales`, `metodo` y `modo_de_coeficientes`: un `UPDATE
grupo_de_reparto SET complejo_id = <otro edificio>` sobre Generales pasaba
sin error — el edificio original quedaba sin Generales (equivale al DELETE
que el trigger prohíbe) y su alcance cambiaba. La FK compuesta no alcanza:
sólo impide otra ADMINISTRACIÓN, nunca otro edificio de la misma (la spec
`grupos-de-reparto/spec.md` exige que todo edificio tenga Generales y que
su alcance no cambie).

No se edita 0011 (ya aplicada): esta migración reemplaza la función con
`CREATE OR REPLACE` sumando `complejo_id` y `administracion_id` a la
comparación; el downgrade restaura exactamente la definición de 0011.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
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
    """)


def downgrade() -> None:
    op.execute("""
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
            ) THEN
                RAISE EXCEPTION
                    'Generales no admite cambiar es_generales, metodo ni modo_de_coeficientes';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
