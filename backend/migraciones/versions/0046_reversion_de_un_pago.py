"""Revertir un pago informado (pagos-informados, H-022, R18, P29, D-163).

1. `tipo_de_movimiento` suma `interes_por_reversion` (débito): el interés de los días ya cobrados
   con el pago adentro, que al revertirlo se cobra por la diferencia. Es un débito del componente
   `interes` enlazado al interés que completa (`enlazado_a`, como el ajuste de D-085). Lo exige
   `ck_mov_interes_por_reversion`: obligación, componente interés y enlace.
2. `reversion_de_pago` (sembrado desde la `0023`) pasa a poder corregir un movimiento: un
   `reversion_de_pago` lleva `corrige_a` (el `pago` vigente de la parte) y su motivo. Hasta ahora
   `ck_mov_corrige_tipo` sólo lo admitía para `correccion`; ahora lo admite también para
   `reversion_de_pago`, y `ck_mov_reversion_de_pago` le exige corregir algo y tener motivo.
3. El vocabulario de auditoría suma `revertir_pago_informado`: revertir es un evento del pago, no
   un permiso nuevo (`revertir_o_reimputar_pago` ya estaba).

Esta migración hace `ALTER` sobre una tabla protegida (`movimiento`): lo declara en
`PRESTA_PROPIEDAD` y `roles antes` se la presta al migrador sólo mientras está pendiente (D-115.3,
L-088); `roles despues` la devuelve. No importa `Accion` (L-089): el vocabulario va literal.

Revision ID: 0046
Revises: 0045
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

#: Las tablas protegidas que esta migración altera (D-115.3): `roles antes` las presta.
PRESTA_PROPIEDAD: tuple[str, ...] = ("movimiento",)


def upgrade() -> None:
    op.execute("""
        INSERT INTO tipo_de_movimiento (tipo,sentido) VALUES ('interes_por_reversion','debito');
        INSERT INTO accion_de_auditoria (nombre) VALUES ('revertir_pago_informado');
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_corrige_tipo;
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_corrige_tipo CHECK (corrige_a IS NULL OR
        tipo IN ('correccion','reversion_de_pago'));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_reversion_de_pago CHECK
        (tipo<>'reversion_de_pago' OR (corrige_a IS NOT NULL AND motivo IS NOT NULL AND
        length(motivo) BETWEEN 1 AND 500 AND btrim(motivo)<>''));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_interes_por_reversion CHECK
        (tipo<>'interes_por_reversion' OR (obligacion_id IS NOT NULL AND componente IS NOT NULL
        AND componente='interes' AND enlazado_a IS NOT NULL));
    """)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute("ALTER TABLE movimiento NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM movimiento
                   WHERE tipo IN ('reversion_de_pago','interes_por_reversion')) THEN
            RAISE EXCEPTION 'hay pagos revertidos: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute("""
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_interes_por_reversion;
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_reversion_de_pago;
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_corrige_tipo;
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_corrige_tipo CHECK (corrige_a IS NULL OR
        tipo='correccion');
        DELETE FROM tipo_de_movimiento WHERE tipo='interes_por_reversion';
        ALTER TABLE movimiento FORCE ROW LEVEL SECURITY;
    """)
    # La FK 23503 preserva todo evento utilizado: si ya se auditó una reversión, no se baja.
    op.execute("DELETE FROM accion_de_auditoria WHERE nombre='revertir_pago_informado'")
