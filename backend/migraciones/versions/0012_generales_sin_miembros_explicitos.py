"""Generales tiene alcance implícito, nunca filas en grupo_unidad (R3B-6).

La unidad nueva entra por la consulta de todas las unidades del edificio:
esta barrera no afecta su alta ni la edición de grupos parciales.
El preflight mira todas las administraciones como dueño, bajo bloqueo y en
la transacción de Alembic: NO FORCE sólo durante esa lectura; al fallar,
el rollback conserva FORCE. No se deshabilita RLS ni se cambian políticas.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("LOCK TABLE grupo_de_reparto, grupo_unidad IN ACCESS EXCLUSIVE MODE")
    for tabla in ("grupo_de_reparto", "grupo_unidad"):
        op.execute(f"ALTER TABLE {tabla} NO FORCE ROW LEVEL SECURITY")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM grupo_unidad AS m
                JOIN grupo_de_reparto AS g ON
                    (g.administracion_id, g.complejo_id, g.id) =
                    (m.administracion_id, m.complejo_id, m.grupo_id)
                WHERE g.es_generales
            ) THEN
                RAISE EXCEPTION 'Generales tiene miembros explícitos; corregir antes de migrar';
            END IF;
        END $$
    """)
    for tabla in ("grupo_de_reparto", "grupo_unidad"):
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE FUNCTION fn_generales_sin_miembros_explicitos() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        DECLARE generales boolean;
        BEGIN
            SELECT g.es_generales INTO generales FROM public.grupo_de_reparto AS g
            WHERE (g.administracion_id, g.complejo_id, g.id) =
                (NEW.administracion_id, NEW.complejo_id, NEW.grupo_id)
            FOR SHARE;
            IF generales THEN
                RAISE EXCEPTION 'Generales no admite miembros explícitos';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE FUNCTION fn_generales_sin_promocion_con_miembros() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        BEGIN
            IF NEW.es_generales AND NOT OLD.es_generales AND EXISTS (
                SELECT 1 FROM public.grupo_unidad AS m
                WHERE (m.administracion_id, m.complejo_id, m.grupo_id) =
                    (NEW.administracion_id, NEW.complejo_id, NEW.id)
            ) THEN
                RAISE EXCEPTION 'Generales no admite miembros explícitos';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute(
        "CREATE TRIGGER trg_generales_sin_miembros BEFORE INSERT OR UPDATE ON grupo_unidad "
        "FOR EACH ROW EXECUTE FUNCTION fn_generales_sin_miembros_explicitos()"
    )
    op.execute(
        "CREATE TRIGGER trg_generales_sin_promocion BEFORE UPDATE OF es_generales "
        "ON grupo_de_reparto FOR EACH ROW "
        "EXECUTE FUNCTION fn_generales_sin_promocion_con_miembros()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_generales_sin_promocion ON grupo_de_reparto")
    op.execute("DROP TRIGGER trg_generales_sin_miembros ON grupo_unidad")
    op.execute("DROP FUNCTION fn_generales_sin_promocion_con_miembros()")
    op.execute("DROP FUNCTION fn_generales_sin_miembros_explicitos()")
