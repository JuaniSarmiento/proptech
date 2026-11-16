"""Distribuir una liquidación emitida (E9, D-157): el puerto único que usan la ruta manual (H-014),
el portal (11) y el email (13).

`registrar_distribucion` agrega el evento `distribuida` en la transacción del llamador, una vez por
emisión (el primero gana y su `origen` queda). Toma el candado del período (E5, la fila de
`complejo` antes que cualquier cuenta), así que distribuir y anular se serializan: una de las dos
gana y la otra encuentra el estado ya cambiado. No audita ni commitea: lo hace quien lo llama.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion import errores as libro
from proptech_core.cuenta_corriente.aplicacion.creditos import ahora_utc
from proptech_core.cuenta_corriente.aplicacion.emisiones import (
    ORIGENES_DE_DISTRIBUCION,
    distribuir_emision,
)
from proptech_core.liquidacion.aplicacion.errores import Conflicto, EntradaInvalida, NoEncontrado

__all__ = ["ORIGENES_DE_DISTRIBUCION", "registrar_distribucion"]


def registrar_distribucion(
    sesion: Session,
    *,
    emision_id: UUID,
    origen: str,
    persona_id: UUID | None,
    request_id: UUID,
    reloj: Callable[[], datetime] = ahora_utc,
) -> bool:
    """`True` si la registró; `False` si ya estaba distribuida (idempotente, sin escribir). Una
    emisión anulada es `Conflicto("estado", "anulada")`; una que no existe, `NoEncontrado`."""
    complejo = sesion.execute(
        text("SELECT complejo_id FROM liquidacion WHERE emision_id = :e"), {"e": emision_id}
    ).scalar_one_or_none()
    if complejo is None or cargar_complejo(sesion, UUID(str(complejo)), bloquear=True) is None:
        raise NoEncontrado
    try:
        return distribuir_emision(
            sesion,
            emision_id=emision_id,
            origen=origen,
            persona_id=persona_id,
            request_id=request_id,
            reloj=reloj,
        )
    except libro.Conflicto:
        raise Conflicto("estado", "anulada") from None
    except libro.NoEncontrado:
        raise NoEncontrado from None
    except libro.EntradaInvalida as error:
        raise EntradaInvalida(error.campo, donde="body") from None
