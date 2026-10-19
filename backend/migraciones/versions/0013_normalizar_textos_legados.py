"""Recorte de R3A-6 en filas existentes y futuras escrituras SQL (R3B-8).

Se normaliza todo, salvo colisiones: el preflight aborta sin tocar filas y
sin repetir valores. La copia congelada de espacios de str.strip (Python
3.14) mantiene estable la migración; el test compara contra isspace.
NO FORCE permite al dueño migrar todos los tenants, únicamente dentro de
la transacción y bajo ACCESS EXCLUSIVE. FORCE vuelve antes del commit;
cualquier error revierte también el cambio de FORCE y alembic_version.
El downgrade quita las guardas, no repone espacios que ya fueron recortados.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLAS = ("complejo", "unidad", "grupo_de_reparto", "categoria_de_gasto")
_ESPACIOS = (
    r"\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680"
    r"\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029"
    r"\202F\205F\3000"
)


def upgrade() -> None:
    op.execute("LOCK TABLE " + ", ".join(_TABLAS) + " IN ACCESS EXCLUSIVE MODE")
    op.execute(f"""
        CREATE FUNCTION fn_recortar_texto_3a(valor text) RETURNS text
        LANGUAGE sql IMMUTABLE STRICT SET search_path = '' AS $$
            SELECT pg_catalog.btrim(valor, U&'{_ESPACIOS}')
        $$
    """)
    for tabla in _TABLAS:
        op.execute(f"ALTER TABLE {tabla} NO FORCE ROW LEVEL SECURITY")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM unidad
                GROUP BY administracion_id, complejo_id, public.fn_recortar_texto_3a(identificador)
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'normalización: colisión en unidad.identificador; resolver primero';
            END IF;
            IF EXISTS (
                SELECT 1 FROM categoria_de_gasto
                GROUP BY administracion_id, complejo_id, lower(public.fn_recortar_texto_3a(nombre))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'normalización: colisión en categoria_de_gasto.nombre; resolver primero';
            END IF;
        END $$
    """)
    op.execute("UPDATE unidad SET identificador = public.fn_recortar_texto_3a(identificador)")
    op.execute("UPDATE complejo SET nombre = public.fn_recortar_texto_3a(nombre)")
    op.execute("UPDATE grupo_de_reparto SET nombre = public.fn_recortar_texto_3a(nombre)")
    op.execute("UPDATE categoria_de_gasto SET nombre = public.fn_recortar_texto_3a(nombre)")
    op.execute("UPDATE complejo SET localidad = public.fn_recortar_texto_3a(localidad)")
    for tabla in _TABLAS:
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE FUNCTION fn_recortar_campos_3a() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        BEGIN
            IF TG_TABLE_NAME = 'unidad' THEN
                NEW.identificador = public.fn_recortar_texto_3a(NEW.identificador);
            ELSE
                NEW.nombre = public.fn_recortar_texto_3a(NEW.nombre);
                IF TG_TABLE_NAME = 'complejo' THEN
                    NEW.localidad = public.fn_recortar_texto_3a(NEW.localidad);
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    for tabla in _TABLAS:
        op.execute(
            f"CREATE TRIGGER trg_recortar_textos_3a BEFORE INSERT OR UPDATE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION fn_recortar_campos_3a()"
        )


def downgrade() -> None:
    for tabla in _TABLAS:
        op.execute(f"DROP TRIGGER trg_recortar_textos_3a ON {tabla}")
    op.execute("DROP FUNCTION fn_recortar_campos_3a()")
    op.execute("DROP FUNCTION fn_recortar_texto_3a(text)")
