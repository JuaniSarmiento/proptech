"""El traslado de la deuda previa al vendedor (cambio-de-titular, H-031, R32, D-168.2).

1. `obligacion` admite capital en cero: la obligación de la cuenta de persona del vendedor es el
   "contenedor" de lo trasladado y su deuda vive en los débitos `traslado` (uno por componente, del
   mismo importe que el crédito que los originó). Sólo la admite una obligación que no viene de una
   emisión: `num_nonnulls(emision_id, operacion_id) = 1` ya la obliga a tener `operacion_id`, y la
   emitida sigue exigiendo capital (`ck_obligacion_importes`).
2. `traslado` (sembrado desde la `0023`, débito y crédito) pasa a poder usarse con su forma real:
   siempre sobre una obligación y un componente, y el débito de la cuenta del vendedor enlazado
   (`enlazado_a`, de otra cuenta, E14 del 4b) al crédito de la unidad que lo originó
   (`ck_mov_traslado`).
3. `cambio_de_titular.vendedor_deudor_id`: a nombre de cuál vendedor quedó la deuda (nulo si la
   deuda quedó en la unidad). Sin `CHECK` cruzado con `deuda_previa`: las filas de H-030 no la
   traen.

Hace `ALTER` sobre tablas protegidas (`obligacion`, `movimiento`, `cambio_de_titular`): lo declara
en `PRESTA_PROPIEDAD` (D-115.3, L-088). No importa `Accion` (L-089).

Revision ID: 0051
Revises: 0050
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

#: Las tablas protegidas que esta migración altera (D-115.3): `roles antes` las presta.
PRESTA_PROPIEDAD: tuple[str, ...] = ("obligacion", "movimiento", "cambio_de_titular")


def upgrade() -> None:
    op.execute("""
        ALTER TABLE obligacion DROP CONSTRAINT ck_obligacion_importes;
        ALTER TABLE obligacion ADD CONSTRAINT ck_obligacion_importes CHECK (ordinaria>=0 AND
        fondo_de_reserva>=0 AND extraordinaria>=0 AND (ordinaria+fondo_de_reserva+extraordinaria>0
        OR (emision_id IS NULL AND operacion_id IS NOT NULL)));
        ALTER TABLE movimiento ADD CONSTRAINT ck_mov_traslado CHECK
        (tipo<>'traslado' OR (obligacion_id IS NOT NULL AND componente IS NOT NULL
        AND (sentido='credito' OR enlazado_a IS NOT NULL)));
        ALTER TABLE cambio_de_titular ADD COLUMN vendedor_deudor_id UUID;
        ALTER TABLE cambio_de_titular ADD CONSTRAINT fk_cambio_vendedor_deudor FOREIGN KEY
        (administracion_id,vendedor_deudor_id) REFERENCES persona (administracion_id,id);
    """)


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    op.execute("ALTER TABLE movimiento NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE obligacion NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE cambio_de_titular NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM movimiento WHERE tipo = 'traslado')
           OR EXISTS (SELECT 1 FROM cambio_de_titular WHERE vendedor_deudor_id IS NOT NULL) THEN
            RAISE EXCEPTION 'hay deuda trasladada al vendedor: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    op.execute("""
        ALTER TABLE cambio_de_titular DROP CONSTRAINT fk_cambio_vendedor_deudor;
        ALTER TABLE cambio_de_titular DROP COLUMN vendedor_deudor_id;
        ALTER TABLE movimiento DROP CONSTRAINT ck_mov_traslado;
        ALTER TABLE obligacion DROP CONSTRAINT ck_obligacion_importes;
        ALTER TABLE obligacion ADD CONSTRAINT ck_obligacion_importes CHECK (ordinaria>=0 AND
        fondo_de_reserva>=0 AND extraordinaria>=0 AND ordinaria+fondo_de_reserva+extraordinaria>0);
        ALTER TABLE cambio_de_titular FORCE ROW LEVEL SECURITY;
        ALTER TABLE obligacion FORCE ROW LEVEL SECURITY;
        ALTER TABLE movimiento FORCE ROW LEVEL SECURITY;
    """)
