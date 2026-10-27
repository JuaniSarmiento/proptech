"""Pisos del edificio y de la unidad (D3, D9, corrección DBA-1).

`complejo.pisos` (nullable, 1 a 60) y `complejo.subsuelos` (nullable, 0 a
5) nacen **sin calcular nada** de las unidades existentes: no hace falta
ningún `UPDATE` de backfill para agregar columnas nullable (D3, corrección
DBA-1 — la versión anterior de esta migración las hacía `NOT NULL`
calculadas con un `UPDATE` que, bajo RLS forzada y sin `BYPASSRLS` en
`proptech_migrador`, veía cero filas sin avisar; el DBA lo encontró antes
de construir).

`unidad.piso` sí necesita una transformación real de datos existentes
(texto libre → el vocabulario nuevo), así que es la única parte de este
change que usa el candado de D9 (igual que `0012`/`0013`/`0017`/`0018`):
`LOCK TABLE unidad IN ACCESS EXCLUSIVE MODE` → `ALTER TABLE unidad NO
FORCE ROW LEVEL SECURITY` → el `UPDATE` que mapea → `ALTER TABLE unidad
FORCE ROW LEVEL SECURITY`, todo en la misma transacción de Alembic.

Mapeo (coincidencia exacta, sin recortar espacios, sin distinguir
mayúsculas de minúsculas aposta): `'PB'` → `'PB'`, `'SS'` → `'SS1'`, un
entero de `1` a `60` como texto → ese mismo texto, cualquier otra cosa
(vacío, `'pb'`, `' 2 '`, `'1°'`, `'Entrepiso'`, `'SS2'` sin más contexto)
→ `NULL` ("sin completar", nunca un valor inventado).

El `CHECK` de forma `^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$` se agrega DESPUÉS
del `UPDATE`: si se agregara antes, el `UPDATE` que todavía no corrió
podría dejar valores fuera de ese patrón (el texto libre viejo) y la
migración fallaría a mitad de camino.

Bajada: mismo candado para `unidad.piso` (`UPDATE unidad SET piso = ''
WHERE piso IS NULL` — el `server_default` original de `0005`, nunca
`'PB'` ni ningún valor con significado) antes de devolver la columna a
`NOT NULL`; pierde qué filas estaban "sin completar" (vuelven a `''`,
indistinguibles de un dato viejo vacío) — es el punto de no retorno de
esta migración. Las columnas del edificio se borran sin más: ya eran
nullable, no hay dato que perder.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_PATRON_PISO = r"^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$"


def upgrade() -> None:
    # 1) Pisos y subsuelos del edificio: nullable, sin backfill (D3/DBA-1).
    op.add_column("complejo", sa.Column("pisos", sa.Integer(), nullable=True))
    op.add_column("complejo", sa.Column("subsuelos", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_complejo_pisos", "complejo", "pisos IS NULL OR (pisos BETWEEN 1 AND 60)"
    )
    op.create_check_constraint(
        "ck_complejo_subsuelos", "complejo", "subsuelos IS NULL OR (subsuelos BETWEEN 0 AND 5)"
    )

    # 2) unidad.piso pasa a nullable y se mapea bajo el candado de D9.
    op.alter_column("unidad", "piso", nullable=True)
    op.execute("LOCK TABLE unidad IN ACCESS EXCLUSIVE MODE")
    op.execute("ALTER TABLE unidad NO FORCE ROW LEVEL SECURITY")
    op.execute("""
        UPDATE unidad SET piso = CASE
            WHEN piso = 'PB' THEN 'PB'
            WHEN piso = 'SS' THEN 'SS1'
            WHEN piso ~ '^([1-9]|[1-5][0-9]|60)$' THEN piso
            ELSE NULL
        END
    """)
    op.execute("ALTER TABLE unidad FORCE ROW LEVEL SECURITY")
    # Recién ahora, con todas las filas ya mapeadas: el CHECK de forma.
    op.create_check_constraint(
        "ck_unidad_piso", "unidad", f"piso IS NULL OR piso ~ '{_PATRON_PISO}'"
    )


def downgrade() -> None:
    op.drop_constraint("ck_unidad_piso", "unidad", type_="check")
    op.execute("LOCK TABLE unidad IN ACCESS EXCLUSIVE MODE")
    op.execute("ALTER TABLE unidad NO FORCE ROW LEVEL SECURITY")
    op.execute("UPDATE unidad SET piso = '' WHERE piso IS NULL")
    op.execute("ALTER TABLE unidad FORCE ROW LEVEL SECURITY")
    op.alter_column("unidad", "piso", nullable=False)

    op.drop_constraint("ck_complejo_subsuelos", "complejo", type_="check")
    op.drop_constraint("ck_complejo_pisos", "complejo", type_="check")
    op.drop_column("complejo", "subsuelos")
    op.drop_column("complejo", "pisos")
