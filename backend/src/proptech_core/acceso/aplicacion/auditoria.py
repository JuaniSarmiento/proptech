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

from proptech_core.acceso.dominio.eventos import EventoDeAcceso, EventoDelGasto, EventoDelPadron
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion

#: Alias corto para el vocabulario completo auditable (D9 + `gastos-y-cargos`).
_Accionable = Accion | EventoDeAcceso | EventoDelPadron | EventoDelGasto


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
    persona_id: UUID
    asignacion_id: UUID


class _DetalleCorreccion(_DetalleAsignarEdificio):
    forma: Literal["contra_asiento", "credito"]
    corrige: UUID


class _DetalleConfiguracion(_DetalleAsignarEdificio):
    vigente_desde: date


class _DetallePersonaAsignacion(_DetalleBase):
    persona_id: UUID
    asignacion_id: UUID


class _DetalleInvitarPersonal(_DetalleBase):
    persona_id: UUID
    asignacion_id: UUID
    rol: Literal["administrador", "contador", "auxiliar", "consejo"]
    alcance: Literal["principal", "edificio"]


class _DetalleIngresoFallido(_DetalleBase):
    motivo: Literal["sin_asignacion"]


class _CambioCoeficiente(_DetalleBase):
    anterior: str | None
    nuevo: str | None


class _CambioCoeficienteMiembro(_CambioCoeficiente):
    unidad_id: UUID


class _CambiosDeMiembros(_DetalleBase):
    entraron: list[UUID]
    salieron: list[UUID]


class _DetalleCrearUnidad(_DetalleAsignarEdificio):
    campos: list[Literal["identificador", "tipo", "piso", "coeficiente", "superficie_m2"]]
    coeficiente: _CambioCoeficiente | None = None


class _DetalleEditarUnidad(_DetalleCrearUnidad):
    pass


class _DetalleCrearGrupo(_DetalleAsignarEdificio):
    campos: list[Literal["clave", "nombre", "metodo", "modo_de_coeficientes", "unidades"]]
    coeficientes: list[_CambioCoeficienteMiembro] | None = None


class _DetalleEditarGrupo(_DetalleAsignarEdificio):
    campos: list[Literal["clave", "nombre", "metodo", "activo"]]


class _DetalleFijarUnidades(_DetalleAsignarEdificio):
    campos: list[Literal["modo_de_coeficientes", "unidades"]]
    coeficientes: list[_CambioCoeficienteMiembro] | None = None
    miembros: _CambiosDeMiembros | None = None


class _DetalleEditarCategoria(_DetalleAsignarEdificio):
    campos: list[Literal["nombre", "activa"]]


class _DetalleReordenarCategorias(_DetalleAsignarEdificio):
    campos: list[Literal["orden"]]


class _DetalleEditarEdificio(_DetalleAsignarEdificio):
    campos: list[
        Literal[
            "nombre",
            "provincia_id",
            "departamento_id",
            "localidad_id",
            "calle_y_numero",
            "pisos",
            "subsuelos",
        ]
    ]


class _DetalleCrearProveedor(_DetalleAsignarEdificio):
    pass


class _DetalleEditarProveedor(_DetalleAsignarEdificio):
    campos: list[Literal["razon_social", "activo"]]


class _DetalleCrearGasto(_DetalleAsignarEdificio):
    pass


class _DetalleEditarGasto(_DetalleAsignarEdificio):
    #: Sólo nombres de campo (nunca el valor, D9): "importe" puede figurar
    #: acá, listado, mientras el gasto editable (borrador/sin_ia/en_revision)
    #: cambie su monto — lo que el detalle nunca lleva es el VALOR del monto.
    campos: list[
        Literal[
            "concepto",
            "categoria_id",
            "grupo_id",
            "periodo",
            "tipo",
            "importe",
            "proveedor_id",
            "cuit_emisor",
            "punto_de_venta",
            "tipo_de_comprobante",
            "numero_de_comprobante",
            "documento_receptor",
        ]
    ]


class _DetalleAprobarGasto(_DetalleAsignarEdificio):
    pass


class _DetalleCargarNotaDeCredito(_DetalleAsignarEdificio):
    gasto_id: UUID


class _DetalleCrearCargoParticular(_DetalleAsignarEdificio):
    unidad_id: UUID


class _DetalleEditarCargoParticular(_DetalleAsignarEdificio):
    campos: list[Literal["concepto", "periodo", "importe", "unidad_id", "motivo"]]


class _DetalleAprobarCargoParticular(_DetalleAsignarEdificio):
    unidad_id: UUID


class _DetalleImportarCargosParticulares(_DetalleAsignarEdificio):
    cantidad: int


#: Un modelo por Accion que se audita CON detalle (D9). Una Accion sin
#: entrada acá usa `_DetalleBase` (ningún campo, ningún detalle permitido).
_MODELOS_DE_DETALLE: dict[_Accionable, type[_DetalleBase]] = {
    EventoDelPadron.CREAR_UNIDAD: _DetalleCrearUnidad,
    EventoDelPadron.EDITAR_UNIDAD: _DetalleEditarUnidad,
    EventoDelPadron.CREAR_GRUPO: _DetalleCrearGrupo,
    EventoDelPadron.EDITAR_GRUPO: _DetalleEditarGrupo,
    EventoDelPadron.FIJAR_UNIDADES: _DetalleFijarUnidades,
    EventoDelPadron.EDITAR_CATEGORIA: _DetalleEditarCategoria,
    EventoDelPadron.REORDENAR_CATEGORIAS: _DetalleReordenarCategorias,
    EventoDelPadron.EDITAR_EDIFICIO: _DetalleEditarEdificio,
    EventoDeAcceso.DAR_DE_ALTA_VECINO: _DetallePersonaAsignacion,
    EventoDeAcceso.INVITAR_PERSONAL: _DetalleInvitarPersonal,
    EventoDeAcceso.INGRESO_FALLIDO: _DetalleIngresoFallido,
    Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS: _DetalleAsignacion,
    Accion.CREAR_EDIFICIO: _DetalleAsignarEdificio,
    Accion.CORREGIR_MOVIMIENTO: _DetalleCorreccion,
    Accion.CREAR_VERSION_DE_CONFIGURACION: _DetalleConfiguracion,
    Accion.CONFIRMAR_SIN_SALDOS_PREVIOS: _DetalleAsignarEdificio,
    EventoDelGasto.CREAR_PROVEEDOR: _DetalleCrearProveedor,
    EventoDelGasto.EDITAR_PROVEEDOR: _DetalleEditarProveedor,
    EventoDelGasto.CREAR_GASTO: _DetalleCrearGasto,
    EventoDelGasto.EDITAR_GASTO: _DetalleEditarGasto,
    EventoDelGasto.APROBAR_GASTO: _DetalleAprobarGasto,
    EventoDelGasto.CARGAR_NOTA_DE_CREDITO: _DetalleCargarNotaDeCredito,
    EventoDelGasto.CREAR_CARGO_PARTICULAR: _DetalleCrearCargoParticular,
    EventoDelGasto.EDITAR_CARGO_PARTICULAR: _DetalleEditarCargoParticular,
    EventoDelGasto.APROBAR_CARGO_PARTICULAR: _DetalleAprobarCargoParticular,
    EventoDelGasto.IMPORTAR_CARGOS_PARTICULARES: _DetalleImportarCargosParticulares,
}


def _detalle_validado(accion: _Accionable, detalle: dict[str, Any]) -> dict[str, Any]:
    modelo = _MODELOS_DE_DETALLE.get(accion, _DetalleBase)
    try:
        validado = modelo.model_validate(detalle)
    except ValidationError as error:
        # Nunca el valor recibido (L-007): sólo los nombres de los campos
        # con problema, tal como pydantic ya los separa en `loc`.
        claves = sorted({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        detalle_claves = ", ".join(claves) if claves else "(sin nombre de campo)"
        raise DetalleInvalido(f"detalle inválido para {accion.value}: {detalle_claves}") from None
    return validado.model_dump(mode="json", exclude_unset=True)


def registrar(
    sesion: Session,
    identidad: Identidad,
    accion: _Accionable,
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
_CASOS_SENSIBLES: dict[_Accionable, Callable[..., Any]] = {}


def accion_sensible(
    accion: _Accionable,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Marca `funcion` como el caso de uso que audita `accion` (D9): no
    cambia su comportamiento, sólo la suma al registro que recorre el test
    de la tarea 6.2."""

    def decorador(funcion: Callable[_P, _R]) -> Callable[_P, _R]:
        if anterior := _CASOS_SENSIBLES.get(accion):
            raise ValueError(
                f"{accion.value}: casos sensibles duplicados: "
                f"{anterior.__qualname__} y {funcion.__qualname__}"
            )
        _CASOS_SENSIBLES[accion] = funcion

        @functools.wraps(funcion)
        def envoltura(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def casos_sensibles_registrados() -> dict[_Accionable, Callable[..., Any]]:
    """Copia del registro (nunca el dict real): quien lo use no puede
    mutarlo por accidente."""
    return dict(_CASOS_SENSIBLES)
