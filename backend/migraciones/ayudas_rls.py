"""Ayuda de migración para el candado por administración (D5, cambio 2a).

`aislar_por_administracion(tabla)` deja una tabla con RLS forzada, la
política de lectura/escritura de D5 y el `GRANT` explícito a `proptech_app`
(no basta con los `DEFAULT PRIVILEGES` del paso de roles para que el
guardián del catálogo, 3.2, vea el permiso sin ambigüedad). Los nombres de
tabla son siempre literales fijos en el código de la migración, nunca un
valor que llegue de afuera: la composición por f-string es la misma que usan
los ejemplos oficiales de Alembic para DDL con nombres dinámicos.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

#: El único rol que necesita leer y escribir estas tablas (D1). Nombre fijo
#: a propósito: lo crea `roles.py`, no una variable de entorno de la migración.
_ROL_DE_LA_APP = "proptech_app"


def aislar_por_administracion(
    tabla: str,
    *,
    columna: str = "administracion_id",
    permisos: str = "SELECT, INSERT, UPDATE, DELETE",
) -> None:
    """RLS forzada + la política de D5 + el `GRANT` a la app.

    `columna` es `administracion_id` para toda tabla que cuelga de una
    administración; `administracion` misma se aísla por su propio `id`
    (pasando `columna="id"`), porque no tiene una columna `administracion_id`.

    `permisos` es explícito y no decorativo para `auditoria` (D9, tarea 6.1):
    ahí se pasa `"SELECT, INSERT"`. Eso documenta la intención, pero **no basta**:
    el migrador corre esta migración, y `ALTER DEFAULT PRIVILEGES` (que fija
    `roles.antes()`) le da a la app `UPDATE`/`DELETE` sobre cualquier tabla
    nueva del migrador sin importar qué `GRANT` explícito haga la migración.
    El `REVOKE` real de esos dos permisos pasa en `roles.despues()`.
    """
    op.execute(text(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY'))
    op.execute(text(f'ALTER TABLE "{tabla}" FORCE ROW LEVEL SECURITY'))
    condicion = f"{columna} = nullif(current_setting('app.administracion_id', true), '')::uuid"
    op.execute(
        text(
            f'CREATE POLICY "{tabla}_por_administracion" ON "{tabla}" '
            f"USING ({condicion}) WITH CHECK ({condicion})"
        )
    )
    op.execute(text(f'GRANT {permisos} ON "{tabla}" TO {_ROL_DE_LA_APP}'))
