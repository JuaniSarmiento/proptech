"""Auditoría de acciones sensibles (D9, cambio 2a, tarea 6.2).

`registrar` exige estar ya dentro de una transacción (`sesion.in_transaction()`)
y hace el `INSERT` en la MISMA sesión: si el caso de uso revierte después (un
error forzado, o una fila que la base rechaza), se lleva la fila de auditoría
con él — es la base de D9, no una convención que cada caller tenga que
recordar.

El detalle se valida contra el modelo Pydantic de esa `Accion`
(`extra="forbid"`, sólo tipos simples) ANTES de tocar la sesión: una clave no
permitida nunca llega a la base, y el mensaje de error nombra la clave, nunca
el valor (D9, L-007).

`@accion_sensible(Accion.X)` marca un caso de uso como auditado, para que un
test recorra los marcados y exija una fila por cada uno (D9).
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from datetime import date
from typing import Any, Literal, ParamSpec, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion


class RegistroFueraDeTransaccion(Exception):
    """`registrar()` exige una sesión ya en transacción (D9)."""


class DetalleInvalido(Exception):
    """El detalle tiene una clave, o le falta una, según el modelo de esa Accion."""


class _DetalleBase(BaseModel):
    """Sin campos: toda Accion sin modelo propio sólo admite detalle vacío."""

    model_config = ConfigDict(extra="forbid")


class _DetalleAsignarEdificio(_DetalleBase):
    complejo_id: UUID


class _DetalleAsignacion(_DetalleAsignarEdificio):
    rol: Literal["administrador", "contador", "auxiliar", "consejo"]
    alcance: Literal["edificio"]


class _DetalleConfiguracion(_DetalleAsignarEdificio):
    vigente_desde: date


#: Un modelo por Accion que se audita CON detalle (D9). Una Accion sin
#: entrada acá usa `_DetalleBase` (ningún campo, ningún detalle permitido).
_MODELOS_DE_DETALLE: dict[Accion, type[_DetalleBase]] = {
    Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: _DetalleAsignacion,
    Accion.CREAR_EDIFICIO: _DetalleAsignarEdificio,
    Accion.CREAR_VERSION_DE_CONFIGURACION: _DetalleConfiguracion,
    Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: _DetalleAsignarEdificio,
}


def _detalle_validado(accion: Accion, detalle: dict[str, Any]) -> dict[str, Any]:
    modelo = _MODELOS_DE_DETALLE.get(accion, _DetalleBase)
    try:
        validado = modelo.model_validate(detalle)
    except ValidationError as error:
        # Nunca el valor recibido (L-007): sólo los nombres de los campos
        # con problema, tal como pydantic ya los separa en `loc`.
        claves = sorted({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        detalle_claves = ", ".join(claves) if claves else "(sin nombre de campo)"
        raise DetalleInvalido(f"detalle inválido para {accion.value}: {detalle_claves}") from None
    return validado.model_dump(mode="json")


def registrar(
    sesion: Session,
    identidad: Identidad,
    accion: Accion,
    *,
    entidad: str,
    entidad_id: UUID,
    request_id: UUID,
    detalle: dict[str, Any] | None = None,
) -> None:
    if not sesion.in_transaction():
        raise RegistroFueraDeTransaccion("registrar() exige una sesión ya en transacción (D9)")
    detalle_validado = _detalle_validado(accion, detalle or {})
    sesion.execute(
        text(
            "INSERT INTO auditoria "
            "(administracion_id, persona_id, accion, entidad, entidad_id, detalle, request_id) "
            "VALUES (:administracion_id, :persona_id, :accion, :entidad, :entidad_id, "
            # CAST(...), nunca ":detalle::jsonb": SQLAlchemy deja un bind
            # pegado a "::" sin sustituir (lo toma como texto literal para no
            # confundirlo con el operador de cast de Postgres), y eso le
            # llega al driver como ":detalle" crudo -> SyntaxError (hallazgo
            # real de la 6.2).
            "CAST(:detalle AS jsonb), :request_id)"
        ),
        {
            "administracion_id": str(identidad.administracion_id),
            "persona_id": str(identidad.persona_id),
            "accion": accion.value,
            "entidad": entidad,
            "entidad_id": str(entidad_id),
            "detalle": json.dumps(detalle_validado),
            "request_id": str(request_id),
        },
    )


_P = ParamSpec("_P")
_R = TypeVar("_R")

#: Caso de uso marcado -> Accion que audita (D9). Nunca se edita a mano
#: fuera del decorador: lo llena `accion_sensible` cuando el módulo del
#: caso de uso se importa.
_CASOS_SENSIBLES: dict[Accion, Callable[..., Any]] = {}


def accion_sensible(accion: Accion) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Marca `funcion` como el caso de uso que audita `accion` (D9): no
    cambia su comportamiento, sólo la suma al registro que recorre el test
    de la tarea 6.2."""

    def decorador(funcion: Callable[_P, _R]) -> Callable[_P, _R]:
        _CASOS_SENSIBLES[accion] = funcion

        @functools.wraps(funcion)
        def envoltura(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def casos_sensibles_registrados() -> dict[Accion, Callable[..., Any]]:
    """Copia del registro (nunca el dict real): quien lo use no puede
    mutarlo por accidente."""
    return dict(_CASOS_SENSIBLES)
