""" "Generales" no se borra ni se desnaturaliza, ni por SQL (3a, R3A-3).

`grupos-de-reparto/spec.md` exige que el método, el modo y el alcance de
"Generales" MUST NOT cambiar y que el grupo MUST NOT poder borrarse — sin
acotarlo a la API, a diferencia de las categorías ("por la API"). Hasta acá
la única barrera era que no hay ruta: `proptech_app` tiene DELETE y UPDATE
sobre `grupo_de_reparto` (D1) y ningún CHECK ni trigger lo impedía. Como
Generales no tiene filas en `grupo_unidad`, el DELETE tampoco choca con
ninguna FK.

El trigger sólo mira las tres columnas que la spec protege
(`es_generales`, `metodo`, `modo_de_coeficientes`): el nombre y la clave de
Generales siguen sin poder tocarse por la API (`_reemplazar`/`editar_grupo`
los bloquean con "Generales es inmutable"), pero no hay motivo de spec para
que la base les ponga un trigger también, y el `ON UPDATE CASCADE` de D15
(0007) sobre `grupo_unidad.modo_de_coeficientes` sigue intacto: sólo se usa
cuando un grupo NO generales cambia de modo, caso que el trigger no toca
(sólo mira `OLD.es_generales`).

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION fn_grupo_generales_protegido() RETURNS trigger
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
    op.execute(
        "CREATE TRIGGER trg_grupo_generales_sin_delete BEFORE DELETE "
        "ON grupo_de_reparto FOR EACH ROW "
        "EXECUTE FUNCTION fn_grupo_generales_protegido()"
    )
    op.execute(
        "CREATE TRIGGER trg_grupo_generales_sin_desnaturalizar BEFORE UPDATE "
        "ON grupo_de_reparto FOR EACH ROW "
        "EXECUTE FUNCTION fn_grupo_generales_protegido()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_grupo_generales_sin_desnaturalizar ON grupo_de_reparto")
    op.execute("DROP TRIGGER trg_grupo_generales_sin_delete ON grupo_de_reparto")
    op.execute("DROP FUNCTION fn_grupo_generales_protegido()")
