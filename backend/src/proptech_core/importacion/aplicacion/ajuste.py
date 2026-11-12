"""Ajuste de saldo inicial (design D8, E6, E11; D-155): corregir, ya confirmada la migración, un
saldo cargado de menos con una obligación nueva y su motivo.

Orden de chequeo (D7 del 2a): alcance (404) -> permiso (403) -> estado de la migración (409,
`estado_migracion`) -> la entrada (422) y el replay por `operacion_id` (en el libro, que escribe
la obligación). Se audita una vez, con ids y sin montos ni motivo; un replay no vuelve a auditar.
No commitea: lo hace el llamador.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import Conflicto, transaccion
from proptech_core.cuenta_corriente.aplicacion.ajustes import (
    AjusteRegistrado,
    registrar_ajuste_de_saldo_inicial,
)
from proptech_core.importacion.aplicacion.edificio import edificio_autorizado

__all__ = ["AjusteRegistrado", "ajustar_saldo_inicial"]


@accion_sensible(Accion.AJUSTAR_SALDO_INICIAL)
def ajustar_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    operacion_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> AjusteRegistrado:
    with transaccion(sesion, {}):
        edificio = edificio_autorizado(sesion, identidad, complejo_id, Accion.AJUSTAR_SALDO_INICIAL)
        if edificio.estado_migracion != "confirmada":
            raise Conflicto("estado_migracion")
        ajuste = registrar_ajuste_de_saldo_inicial(
            sesion,
            identidad,
            complejo_id=complejo_id,
            unidad_id=unidad_id,
            operacion_id=operacion_id,
            importe=importe,
            componente=componente,
            motivo=motivo,
            request_id=request_id,
            reloj=reloj,
        )
        if not ajuste.repetido:
            registrar(
                sesion,
                identidad,
                Accion.AJUSTAR_SALDO_INICIAL,
                entidad="ajuste_de_saldo_inicial",
                entidad_id=ajuste.ajuste_id,
                request_id=request_id,
                detalle={
                    "complejo_id": str(complejo_id),
                    "unidad_id": str(ajuste.unidad_id),
                    "obligacion_id": str(ajuste.obligacion_id),
                    "componente": ajuste.componente,
                },
            )
    return ajuste
