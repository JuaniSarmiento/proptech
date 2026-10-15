"""Casos de uso de escritura de `complejos` (D7, D9, cambio 2a, tarea 6.2).

`asignar_complejo_a_persona` es el único hoy, y el único marcado con
`@accion_sensible`: inserta la fila de `asignacion_rol` y audita la acción
en la MISMA sesión (D9). El bloque usa un `SAVEPOINT`
(`sesion.begin_nested()`) si la sesión ya venía con una transacción abierta
— el caso normal de la API, que ya leyó antes de llegar hasta acá — o una
transacción propia (`sesion.begin()`) si no, como en un caso de uso que abre
su propia sesión. Cualquier excepción dentro del bloque revierte las dos
filas (la de `asignacion_rol` y la de `auditoria`, si llegó a escribirse).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion

_ACCION = Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS


@accion_sensible(_ACCION)
def asignar_complejo_a_persona(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    persona_id: UUID,
    rol: str,
    nivel: str | None,
    request_id: UUID,
) -> UUID:
    bloque = sesion.begin_nested() if sesion.in_transaction() else sesion.begin()
    with bloque:
        fila = sesion.execute(
            text(
                "INSERT INTO asignacion_rol "
                "(administracion_id, persona_id, rol, complejo_id, nivel) "
                "VALUES (:administracion_id, :persona_id, :rol, :complejo_id, :nivel) "
                "RETURNING id"
            ),
            {
                # Siempre de la identidad (D7): nunca de un campo del pedido.
                "administracion_id": str(identidad.administracion_id),
                "persona_id": str(persona_id),
                "rol": rol,
                "complejo_id": str(complejo_id),
                "nivel": nivel,
            },
        ).one()
        registrar(
            sesion,
            identidad,
            _ACCION,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id)},
        )
    # psycopg3 ya devuelve una columna uuid como `uuid.UUID`, incluso en un
    # `text()` crudo; el `str()`/`UUID()` sólo blinda el tipo para mypy.
    return UUID(str(fila.id))
