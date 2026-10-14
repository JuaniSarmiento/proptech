"""Idempotencia de los trabajos del worker (D3): ejecutar un efecto en la
misma transacción que la que registra la clave en `trabajos_hechos`
(migración `0002`), así ejecutar dos veces el mismo trabajo tiene el mismo
efecto que ejecutarlo una vez. Cambio 1c, tarea 5.2.

Escenarios de `cola-de-trabajos`: Trabajo ejecutado dos veces; Dos ejecuciones
simultáneas; El efecto falla después de reservar la clave.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session


def ejecutar_una_vez(
    sesion: Session,
    *,
    clave: str,
    tarea: str,
    request_id: str,
    efecto: Callable[[Session], None],
) -> bool:
    """`INSERT ... ON CONFLICT (clave) DO NOTHING RETURNING clave` reserva la
    clave; si no devolvió fila, ya estaba hecha y no corre el efecto. Si
    devolvió, corre `efecto(sesion)` y confirma todo junto. Si el efecto
    lanza, el rollback se lleva también la clave reservada: un reintento
    puede completar (D3).

    Dos ejecuciones con la misma clave al mismo tiempo: la segunda queda
    bloqueada en el `INSERT` (por el índice único de la PK) hasta que la
    primera confirma o revierte, y recién ahí resuelve si hay fila.
    """
    fila = sesion.execute(
        text(
            "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
            "VALUES (:clave, :tarea, :request_id) "
            "ON CONFLICT (clave) DO NOTHING RETURNING clave"
        ),
        {"clave": clave, "tarea": tarea, "request_id": request_id},
    ).first()
    if fila is None:
        sesion.rollback()
        return False
    try:
        efecto(sesion)
    except Exception:
        sesion.rollback()
        raise
    sesion.commit()
    return True
