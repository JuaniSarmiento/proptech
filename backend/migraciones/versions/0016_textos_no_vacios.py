"""Un texto que queda vacío después del recorte se rechaza en la base (RF-D-2).

Revisión final del cambio `configuracion-del-edificio` (DBA, 19/10/2026).
`0013_normalizar_textos_legados` recorta espacios y Unicode invisible al
borde (R3A-6) y el trigger `trg_recortar_textos_3a` lo hace también en
toda escritura futura; nada impedía que ese recorte dejara `''`: un
`INSERT`/`UPDATE` por SQL (como `proptech_app`) con `''`, o con sólo
espacios, pasaba sin error. La API ya lo rechaza con 422
(`recortado_sin_control` levanta `ValueError` si el recorte queda vacío),
pero la spec pide que la base también lo sostenga (Goal del cambio).

Verificado antes de este `CHECK` (nota en el PR): ningún seed ni dato
legítimo de `backend/`, `config/` o `infra/` usa `''` en estas columnas.

Columnas: `complejo.nombre`, `complejo.localidad`, `grupo_de_reparto.nombre`,
`categoria_de_gasto.nombre`, `unidad.identificador` — las mismas que recorta
`fn_recortar_texto_3a` (0013).

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

#: (tabla, columna, nombre del CHECK).
_COLUMNAS = (
    ("complejo", "nombre", "ck_complejo_nombre_no_vacio"),
    ("complejo", "localidad", "ck_complejo_localidad_no_vacia"),
    ("grupo_de_reparto", "nombre", "ck_grupo_de_reparto_nombre_no_vacio"),
    ("categoria_de_gasto", "nombre", "ck_categoria_de_gasto_nombre_no_vacio"),
    ("unidad", "identificador", "ck_unidad_identificador_no_vacio"),
)


def upgrade() -> None:
    for tabla, columna, nombre_check in _COLUMNAS:
        op.execute(f"ALTER TABLE {tabla} ADD CONSTRAINT {nombre_check} CHECK ({columna} <> '')")


def downgrade() -> None:
    for tabla, _columna, nombre_check in _COLUMNAS:
        op.execute(f"ALTER TABLE {tabla} DROP CONSTRAINT {nombre_check}")
