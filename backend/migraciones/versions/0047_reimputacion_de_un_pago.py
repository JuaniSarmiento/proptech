"""Reimputar un pago informado (pagos-informados, H-023, R25, D-163).

1. `reimputacion` (sembrado desde la `0023`, débito y crédito) pasa a poder usarse con su forma
   real: el débito del origen corrige el movimiento vigente de la parte (`corrige_a`) y lleva su
   motivo; el crédito del destino queda enlazado al débito (`enlazado_a`, que puede ser de otra
   cuenta, E14 del 4b). `ck_mov_corrige_tipo` lo admite y `ck_mov_reimputacion` se lo exige.
2. El vocabulario de auditoría suma `reimputar_pago_informado`: reimputar es un evento del pago, no
   un permiso nuevo (`revertir_o_reimputar_pago` ya estaba).

Hace `ALTER` sobre una tabla protegida (`movimiento`): lo declara en `PRESTA_PROPIEDAD` y `roles
antes` se la presta al migrador sólo mientras está pendiente (D-115.3, L-088); `roles despues` la
devuelve. No importa `Accion` (L-089): el vocabulario va literal.

Revision ID: 0047
Revises: 0046
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

#: Las tablas protegidas que esta migración altera (D-115.3): `roles antes` las presta.
PRESTA_PROPIEDAD: tuple[str, ...] = ("movimiento",)


def upgrade() -> None:
    op.execute("""
        INSERT INTO accion_de_auditoria (nombre) VALUES ('reimputar_pago_informado');
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_corrige_tipo;
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_corrige_tipo CHECK (corrige_a IS NULL OR
        tipo IN ('correccion','reversion_de_pago','reimputacion'));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_reimputacion CHECK
        (tipo<>'reimputacion' OR (sentido='debito' AND corrige_a IS NOT NULL AND motivo IS NOT NULL
        AND length(motivo) BETWEEN 1 AND 500 AND btrim(motivo)<>'')
        OR (sentido='credito' AND corrige_a IS NULL AND enlazado_a IS NOT NULL));
    """)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute("ALTER TABLE movimiento NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM movimiento WHERE tipo = 'reimputacion') THEN
            RAISE EXCEPTION 'hay pagos reimputados: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute("""
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_reimputacion;
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_corrige_tipo;
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_corrige_tipo CHECK (corrige_a IS NULL OR
        tipo IN ('correccion','reversion_de_pago'));
        ALTER TABLE movimiento FORCE ROW LEVEL SECURITY;
    """)
    # La FK 23503 preserva todo evento utilizado: si ya se auditó una reimputación, no se baja.
    op.execute("DELETE FROM accion_de_auditoria WHERE nombre='reimputar_pago_informado'")
