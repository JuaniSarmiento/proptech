"""Situación de cobranza por cuenta y por edificio (design D6, E14, R20, R30).

Es una lectura: sin candados ni escrituras. `fecha` es la fecha de clasificación (E14): decide qué
obligaciones están vencidas y qué versión de configuración rige (gracia y umbral), pero el libro se
lee como está al leer; no reconstruye la deuda de una fecha pasada. Sólo cuentas de unidad: las de
persona quedan fuera hasta el 4d.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.errores import NoEncontrado as EdificioNoEncontrado
from proptech_core.complejos.aplicacion.lectura import configuracion_vigente
from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto, NoEncontrado
from proptech_core.cuenta_corriente.aplicacion.lecturas import (
    SENTENCIA_DEL_EDIFICIO,
    FotoDeCuenta,
    foto,
    fotos_del_edificio,
)
from proptech_core.cuenta_corriente.dominio.cobranza import SituacionDeCobranza, clasificar

#: La del edificio de `lecturas`, acotada a las cuentas de unidad. Conserva el filtro de tenant
#: propio (`c.administracion_id = t.adm`) además de RLS.
SENTENCIA_DE_COBRANZA = SENTENCIA_DEL_EDIFICIO.replace(
    "AND c.complejo_id = :complejo", "AND c.complejo_id = :complejo AND c.unidad_id IS NOT NULL"
)


@dataclass(frozen=True)
class SituacionDeCuenta:
    cuenta_id: UUID
    unidad_id: UUID
    situacion: SituacionDeCobranza


def _version(sesion: Session, complejo_id: UUID, fecha: date) -> dict[str, Any]:
    try:
        version = configuracion_vigente(sesion, complejo_id, fecha)
    except EdificioNoEncontrado:
        # Un edificio que la sesión no ve: es el no encontrado del libro, no un conflicto.
        raise NoEncontrado from None
    if version is None:
        raise Conflicto("configuracion")
    return version


def _clasificar(f: FotoDeCuenta, version: dict[str, Any], fecha: date) -> SituacionDeCobranza:
    return clasificar(
        f.estado,
        fecha=fecha,
        dias_de_gracia=int(version["dias_de_gracia"]),
        umbral=Dinero(version["umbral_saldo_chico"]),
    )


def situacion_de_cuenta(sesion: Session, *, cuenta_id: UUID, fecha: date) -> SituacionDeCobranza:
    f = foto(sesion, cuenta_id)
    if f.unidad_id is None:
        raise NoEncontrado
    return _clasificar(f, _version(sesion, f.complejo_id, fecha), fecha)


def situacion_del_edificio(
    sesion: Session, *, complejo_id: UUID, fecha: date
) -> Sequence[SituacionDeCuenta]:
    version = _version(sesion, complejo_id, fecha)
    return [
        SituacionDeCuenta(f.cuenta_id, f.unidad_id, _clasificar(f, version, fecha))
        for f in fotos_del_edificio(sesion, complejo_id, SENTENCIA_DE_COBRANZA)
        if f.unidad_id is not None
    ]
