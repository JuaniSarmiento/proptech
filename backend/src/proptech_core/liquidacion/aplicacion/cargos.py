"""Cargo cobrado de menos (design E11, R08, D-157): una obligación nueva con motivo y vínculo a la
de origen, sin tocar nada de lo emitido.

Orden de chequeo (el router ya cargó el edificio, 404, y pidió `corregir_movimiento`, 403): la
unidad es de este edificio (404) -> el libro: la entrada (422), el replay por `operacion_id`, el
origen (404) y recién ahí las escrituras. Se audita una vez, con ids y sin montos ni motivo; un
replay no vuelve a auditar. No commitea: lo hace el llamador.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import transaccion
from proptech_core.complejos.aplicacion.lectura import cargar_unidad
from proptech_core.cuenta_corriente.aplicacion.cargos_de_menos import (
    CargoRegistrado,
)
from proptech_core.cuenta_corriente.aplicacion.cargos_de_menos import (
    registrar_cargo_cobrado_de_menos as registrar_en_el_libro,
)
from proptech_core.liquidacion.aplicacion.errores import NoEncontrado

__all__ = ["CargoRegistrado", "registrar_cargo_cobrado_de_menos"]


def registrar_cargo_cobrado_de_menos(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    obligacion_origen_id: UUID,
    operacion_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> CargoRegistrado:
    with transaccion(sesion, {}):
        unidad = cargar_unidad(sesion, unidad_id)
        if unidad is None or unidad.complejo_id != complejo_id:
            raise NoEncontrado  # inexistente, de otro edificio o de otra administración (RLS)
        cargo = registrar_en_el_libro(
            sesion,
            identidad,
            complejo_id=complejo_id,
            unidad_id=unidad_id,
            obligacion_origen_id=obligacion_origen_id,
            operacion_id=operacion_id,
            importe=importe,
            componente=componente,
            motivo=motivo,
            request_id=request_id,
            reloj=reloj,
        )
        if not cargo.repetido:
            registrar(
                sesion,
                identidad,
                Accion.CORREGIR_MOVIMIENTO,
                entidad="cargo_cobrado_de_menos",
                entidad_id=cargo.cargo_id,
                request_id=request_id,
                detalle={
                    "complejo_id": str(complejo_id),
                    "forma": "cargo_cobrado_de_menos",
                    "corrige": str(obligacion_origen_id),
                },
            )
    return cargo
