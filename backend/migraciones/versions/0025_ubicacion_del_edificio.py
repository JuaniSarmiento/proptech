"""Ubicación del edificio: tres ids de Georef + calle y número (D1, D2).

Las cuatro columnas nacen nullable: ningún `UPDATE` de backfill hace falta
para agregarlas (D3/D9: sólo el `UPDATE` de `unidad.piso` en `0026`
necesita el candado de RLS). `complejo.localidad` pasa a nullable y
derivada (D2): la aplicación la escribe desde el nombre de Georef cada vez
que guarda la ubicación; la API deja de aceptarla como entrada (tarea 2.6).

El `CHECK` "los tres o ninguno" exige que `provincia_id`, `departamento_id`
y `localidad_id` sean los tres `NULL` o los tres no `NULL`: la base nunca
guarda una ubicación a medias. `calle_y_numero` no lleva `CHECK` de largo
en la base (igual que `localidad` hoy, H-8): el máximo de 200 y el recorte
de caracteres de control viven sólo en la aplicación (API).

Bajada: con el candado de D9 (`LOCK TABLE ... ACCESS EXCLUSIVE` → `NO
FORCE` → `UPDATE` → `FORCE`, todo en la misma transacción), rellena
`localidad` con `''` donde sea `NULL` — el mismo valor que `0005` usó como
`server_default` para los complejos del 2a, nunca un valor inventado de
Georef — antes de devolverla a `NOT NULL`. Punto de no retorno: la primera
corrección de ubicación hecha en la pantalla nueva pierde la ubicación al
bajar (Migration Plan).

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("complejo", sa.Column("provincia_id", sa.Text(), nullable=True))
    op.add_column("complejo", sa.Column("departamento_id", sa.Text(), nullable=True))
    op.add_column("complejo", sa.Column("localidad_id", sa.Text(), nullable=True))
    op.add_column("complejo", sa.Column("calle_y_numero", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_complejo_ubicacion_completa_o_vacia",
        "complejo",
        "(provincia_id IS NULL AND departamento_id IS NULL AND localidad_id IS NULL) OR "
        "(provincia_id IS NOT NULL AND departamento_id IS NOT NULL AND localidad_id IS NOT NULL)",
    )
    op.alter_column("complejo", "localidad", nullable=True)


def downgrade() -> None:
    op.execute("LOCK TABLE complejo IN ACCESS EXCLUSIVE MODE")
    op.execute("ALTER TABLE complejo NO FORCE ROW LEVEL SECURITY")
    op.execute("UPDATE complejo SET localidad = '' WHERE localidad IS NULL")
    op.execute("ALTER TABLE complejo FORCE ROW LEVEL SECURITY")
    op.alter_column("complejo", "localidad", nullable=False)
    op.drop_constraint("ck_complejo_ubicacion_completa_o_vacia", "complejo", type_="check")
    op.drop_column("complejo", "calle_y_numero")
    op.drop_column("complejo", "localidad_id")
    op.drop_column("complejo", "departamento_id")
    op.drop_column("complejo", "provincia_id")
