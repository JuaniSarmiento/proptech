"""Vocabulario de configuración, literal e independiente del enum (D14).

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ACCIONES = (
    "crear_edificio",
    "crear_version_de_configuracion",
    "confirmar_sin_saldos_previos",
    "configurar_padron",
    "ver_configuracion_del_edificio",
)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": nombre} for nombre in _ACCIONES],
    )


def downgrade() -> None:
    # La FK de auditoría impide borrar un nombre ya utilizado y revierte
    # la migración entera: un historial nuevo exige restaurar el respaldo.
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_ACCIONES)))
