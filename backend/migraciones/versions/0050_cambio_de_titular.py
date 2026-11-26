"""El cambio de titular de una unidad (cambio-de-titular, H-030, D-168, R32).

Dos tablas de sólo agregar (D-115): tres triggers cada una y RLS forzada por administración, y a
cargo del rol de arranque cuando corre `roles despues`.

- `cambio_de_titular`: una fila por cambio, con la unidad, la fecha, las dos opciones de R32
  (`expensa_del_mes` y `deuda_previa`, con su vocabulario cerrado) y quién y cuándo lo registró.
  La base frena todo cruce de edificio o de administración con FK compuestas.
- `parte_de_cambio_de_titular`: las personas de cada lado (`vendedor` o `comprador`), una fila
  por persona, con FK compuesta a `persona`. La misma persona no puede estar dos veces en un
  cambio (único por cambio y persona): ni repetida ni de los dos lados. Del comprador guarda el
  nombre y el email tal como se informaron (la persona reutilizada por email no se renombra).

También suma `registrar_cambio_de_titular` al vocabulario de auditoría (la acción y el evento son
uno solo, D-096). Sin `ALTER` sobre ninguna tabla protegida existente; no importa `Accion`.

Revision ID: 0050
Revises: 0049
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migraciones.ayudas_rls import aislar_por_administracion

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLAS = ("cambio_de_titular", "parte_de_cambio_de_titular")
_ACCION = "registrar_cambio_de_titular"

_DDL = r"""
CREATE TABLE cambio_de_titular (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, unidad_id UUID NOT NULL, fecha DATE NOT NULL,
    expensa_del_mes TEXT NOT NULL, deuda_previa TEXT NOT NULL,
    registrado_por UUID NOT NULL, registrado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE cambio_de_titular ADD CONSTRAINT ck_cambio_expensa_del_mes CHECK
(expensa_del_mes IS NOT NULL AND expensa_del_mes IN ('entera','prorrateo'));
ALTER TABLE cambio_de_titular ADD CONSTRAINT ck_cambio_deuda_previa CHECK
(deuda_previa IS NOT NULL AND deuda_previa IN ('en_la_unidad','a_nombre_del_vendedor'));
ALTER TABLE cambio_de_titular ADD CONSTRAINT uq_cambio_edificio_id UNIQUE
(administracion_id,complejo_id,id);
ALTER TABLE cambio_de_titular ADD CONSTRAINT fk_cambio_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE cambio_de_titular ADD CONSTRAINT fk_cambio_unidad FOREIGN KEY
(administracion_id,complejo_id,unidad_id) REFERENCES unidad (administracion_id,complejo_id,id);
ALTER TABLE cambio_de_titular ADD CONSTRAINT fk_cambio_persona FOREIGN KEY
(administracion_id,registrado_por) REFERENCES persona (administracion_id,id);
CREATE INDEX ix_cambio_unidad ON cambio_de_titular
(administracion_id,unidad_id,fecha DESC,registrado_en DESC);

CREATE TABLE parte_de_cambio_de_titular (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), administracion_id UUID NOT NULL,
    complejo_id UUID NOT NULL, cambio_id UUID NOT NULL, persona_id UUID NOT NULL,
    rol TEXT NOT NULL, orden INTEGER NOT NULL, nombre TEXT, email TEXT
);
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT ck_parte_de_cambio_rol CHECK
(rol IS NOT NULL AND rol IN ('vendedor','comprador'));
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT ck_parte_de_cambio_orden CHECK
(orden IS NOT NULL AND orden >= 0);
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT ck_parte_de_cambio_datos CHECK (
    (rol = 'vendedor' AND nombre IS NULL AND email IS NULL)
    OR (rol = 'comprador' AND nombre IS NOT NULL AND char_length(nombre) BETWEEN 1 AND 80
        AND btrim(nombre) <> '' AND (email IS NULL OR char_length(email) BETWEEN 1 AND 254)));
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT uq_parte_de_cambio UNIQUE
(administracion_id,cambio_id,persona_id);
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT uq_parte_de_cambio_orden UNIQUE
(administracion_id,cambio_id,rol,orden);
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT fk_parte_de_cambio_complejo FOREIGN KEY
(administracion_id,complejo_id) REFERENCES complejo (administracion_id,id);
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT fk_parte_de_cambio_cambio FOREIGN KEY
(administracion_id,complejo_id,cambio_id) REFERENCES cambio_de_titular
(administracion_id,complejo_id,id);
ALTER TABLE parte_de_cambio_de_titular ADD CONSTRAINT fk_parte_de_cambio_persona FOREIGN KEY
(administracion_id,persona_id) REFERENCES persona (administracion_id,id);
"""


def _proteger(tabla: str) -> str:
    funcion = f"fn_{tabla}_bloqueada"
    return f"""
CREATE FUNCTION {funcion}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION '{tabla} no admite %', TG_OP;
END; $$;
CREATE TRIGGER trg_{tabla}_sin_update_delete BEFORE UPDATE OR DELETE ON {tabla}
FOR EACH ROW EXECUTE FUNCTION {funcion}();
CREATE TRIGGER trg_{tabla}_sin_truncate BEFORE TRUNCATE ON {tabla}
FOR EACH STATEMENT EXECUTE FUNCTION {funcion}();
CREATE TRIGGER trg_{tabla}_sin_update_delete_por_sentencia BEFORE UPDATE OR DELETE ON {tabla}
FOR EACH STATEMENT EXECUTE FUNCTION {funcion}();
"""


def upgrade() -> None:
    op.execute(_DDL)
    for tabla in _TABLAS:
        op.execute(_proteger(tabla))
        aislar_por_administracion(tabla)
    op.bulk_insert(
        sa.table("accion_de_auditoria", sa.column("nombre", sa.Text())),
        [{"nombre": _ACCION}],
    )


def downgrade() -> None:
    # El dueño sin tenant debe ver TODAS las filas antes de decidir.
    for tabla in reversed(_TABLAS):
        op.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
    hay_filas = " OR ".join(f'EXISTS (SELECT 1 FROM "{tabla}")' for tabla in _TABLAS)  # noqa: S608
    op.execute(
        f"""DO $$ BEGIN
        IF {hay_filas} THEN
            RAISE EXCEPTION 'hay cambios de titular: la migración no puede bajarse';
        END IF;
    END $$"""
    )
    for tabla in reversed(_TABLAS):
        op.execute(f'DROP TABLE "{tabla}"')
        op.execute(f'DROP FUNCTION "fn_{tabla}_bloqueada"()')
    # La FK de `auditoria` impide retirar el vocabulario usado (23503), como en la `0039`.
    acciones = sa.table("accion_de_auditoria", sa.column("nombre", sa.Text()))
    op.execute(acciones.delete().where(acciones.c.nombre == _ACCION))
