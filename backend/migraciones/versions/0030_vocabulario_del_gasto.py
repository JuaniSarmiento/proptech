"""Vocabulario del gasto (D9 ampliado, auditoria-de-acciones · "Los eventos
del gasto existen en la base"). Reordenada antes de las notas de crédito y
los cargos particulares (ver `design.md` · Migration Plan: la numeración
original las ponía después) porque la auditoría de proveedores (bloque 2
de `tasks.md`, tarea 2.7) ya necesita `crear_proveedor`/`editar_proveedor`
en la base; el resto de los diez eventos se agrega en el mismo lote para
no repetir la migración ni dejar un hueco en la cadena de revisiones.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_EVENTOS = (
    "crear_proveedor",
    "editar_proveedor",
    "crear_gasto",
    "editar_gasto",
    "aprobar_gasto",
    "cargar_nota_de_credito",
    "crear_cargo_particular",
    "editar_cargo_particular",
    "aprobar_cargo_particular",
    "importar_cargos_particulares",
)


def upgrade() -> None:
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": evento} for evento in _EVENTOS],
    )


def downgrade() -> None:
    tabla = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(tabla.delete().where(tabla.c.nombre.in_(_EVENTOS)))
