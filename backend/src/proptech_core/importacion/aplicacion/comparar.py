"""La comparación del borrador vigente de un edificio (design D6, E13). Lectura pura: el permiso es
el de importar (quien puede subir saldos puede verlos; contador, auxiliar, consejo y vecinos, no).

El aviso de E13: con la forma de cálculo vigente **a la fecha de migración** en "mes entero", cada
unidad con deuda avisa que el primer interés del sistema cubre el mes de la migración.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import NoEncontrado
from proptech_core.complejos.aplicacion.lectura import configuracion_vigente
from proptech_core.importacion.aplicacion.borrador import (
    AceptacionRegistrada,
    borrador_vigente,
    comparar_importacion,
    leer_aceptacion,
)
from proptech_core.importacion.aplicacion.edificio import edificio_autorizado
from proptech_core.importacion.dominio.comparacion import UnidadComparada, aviso_de_mes_entero


@dataclass(frozen=True)
class ComparacionDelBorrador:
    importacion_id: UUID
    unidades: tuple[UnidadComparada, ...]
    total_borrador: Dinero
    total_control: Dinero
    unidades_con_diferencia: int
    #: Hay diferencias y todavía no se aceptaron las de **este** borrador.
    requiere_aceptacion: bool
    aceptacion: AceptacionRegistrada | None


def comparar_borrador(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID
) -> ComparacionDelBorrador:
    edificio_autorizado(sesion, identidad, complejo_id, Accion.IMPORTAR_PADRON_Y_SALDOS)
    vigente = borrador_vigente(sesion, complejo_id)
    if vigente is None:
        raise NoEncontrado()
    comparacion = comparar_importacion(sesion, complejo_id, vigente.importacion_id)
    version = configuracion_vigente(sesion, complejo_id, vigente.fecha_de_migracion)
    avisa = version is not None and version["forma_de_calculo"] == "mes_entero"
    aviso = aviso_de_mes_entero(vigente.fecha_de_migracion)
    unidades = tuple(
        replace(u, aviso=aviso) if avisa and u.con_deuda else u for u in comparacion.unidades
    )
    aceptacion = leer_aceptacion(sesion, vigente.importacion_id)
    return ComparacionDelBorrador(
        importacion_id=vigente.importacion_id,
        unidades=unidades,
        total_borrador=comparacion.total_borrador,
        total_control=comparacion.total_control,
        unidades_con_diferencia=comparacion.unidades_con_diferencia,
        requiere_aceptacion=comparacion.unidades_con_diferencia > 0 and aceptacion is None,
        aceptacion=aceptacion,
    )
