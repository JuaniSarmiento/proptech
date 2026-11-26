"""Vocabulario de auditoría `registrar_cobro_de_vendedor` (cambio-de-titular, H-033, D-168.2c).

Igual patrón que `0048_ver_morosidad.py` y `0049_exportar_morosidad.py`: sólo suma una fila de
vocabulario, sin tocar ninguna tabla protegida ni ningún trigger (enmienda E11, D-129). El cobro
de la cuenta del vendedor escribe en tablas que ya existen (`movimiento`, `imputacion`); la fila
de `auditoria` necesita este nombre en `accion_de_auditoria` (D-096). No importa `Accion` (L-089).

Revision ID: 0053
Revises: 0052
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_EVENTOS = ("registrar_cobro_de_vendedor",)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    # La FK de `auditoria` preserva todo evento usado (23503, D9): punto de no retorno firmado,
    # igual que `0048` y `0049`.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
