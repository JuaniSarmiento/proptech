"""Una unidad conserva su edificio y administración durante toda su vida (R3B-5).

Decisión de Juani, 19/10/2026: la barrera también va en la base.
Sólo se protegen las claves de pertenencia de unidad; la edición del padrón
y el ON UPDATE CASCADE de grupo_de_reparto a grupo_unidad (D15) siguen válidos.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION public.fn_unidad_edificio_inmutable() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        BEGIN
            IF NEW.complejo_id IS DISTINCT FROM OLD.complejo_id
                OR NEW.administracion_id IS DISTINCT FROM OLD.administracion_id THEN
                RAISE EXCEPTION USING
                    ERRCODE = '23514',
                    MESSAGE = 'La unidad no admite cambiar complejo_id ni administracion_id';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute(
        "CREATE TRIGGER trg_unidad_edificio_inmutable BEFORE UPDATE ON public.unidad "
        "FOR EACH ROW EXECUTE FUNCTION public.fn_unidad_edificio_inmutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_unidad_edificio_inmutable ON public.unidad")
    op.execute("DROP FUNCTION public.fn_unidad_edificio_inmutable()")
