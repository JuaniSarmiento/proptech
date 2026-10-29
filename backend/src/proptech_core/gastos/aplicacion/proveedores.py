"""Proveedores por edificio (R12, D-019): alta, edición y desactivación,
nunca borrado (mismo patrón que `complejos/aplicacion/categorias.py`).

La capa de permisos (403) y alcance (404, D7) vive en el router de
`proptech_api`, no acá: esta capa es CRUD puro contra la base, auditado.
"""

from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.eventos import EventoDelGasto
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.gastos.aplicacion.errores import (
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.gastos.dominio.proveedor import DatosProveedor

_CONFLICTOS = {"uq_proveedor_cuit": "cuit"}


def listar_proveedores(
    sesion: Session, complejo_id: UUID, *, solo_activos: bool = False
) -> list[dict[str, Any]]:
    return [
        dict(f)
        for f in sesion.execute(
            text(
                "SELECT id, complejo_id, razon_social, cuit, activo FROM proveedor "
                "WHERE complejo_id=:id AND (NOT :solo OR activo) ORDER BY razon_social"
            ),
            {"id": complejo_id, "solo": solo_activos},
        ).mappings()
    ]


def cargar_proveedor(sesion: Session, proveedor_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text("SELECT id, complejo_id, razon_social, cuit, activo FROM proveedor WHERE id=:id"),
            {"id": proveedor_id},
        )
        .mappings()
        .first()
    )
    return dict(fila) if fila is not None else None


@accion_sensible(EventoDelGasto.CREAR_PROVEEDOR)
def crear_proveedor(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    datos: dict[str, Any],
    request_id: UUID,
) -> UUID:
    try:
        entrada = DatosProveedor.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None
    with transaccion(sesion, _CONFLICTOS):
        proveedor_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO proveedor (administracion_id, complejo_id, "
                        "razon_social, cuit) "
                        "VALUES (:admin, :complejo, :razon_social, :cuit) RETURNING id"
                    ),
                    {
                        **entrada.model_dump(),
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                    },
                ).scalar_one()
            )
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.CREAR_PROVEEDOR,
            entidad="proveedor",
            entidad_id=proveedor_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id)},
        )
    return proveedor_id


@accion_sensible(EventoDelGasto.EDITAR_PROVEEDOR)
def editar_proveedor(
    sesion: Session,
    identidad: Identidad,
    *,
    proveedor_id: UUID,
    cambios: dict[str, Any],
    request_id: UUID,
) -> None:
    with transaccion(sesion, _CONFLICTOS):
        fila = (
            sesion.execute(
                text(
                    "SELECT complejo_id, razon_social, cuit, activo FROM proveedor "
                    "WHERE id=:id FOR UPDATE"
                ),
                {"id": proveedor_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        nueva_razon_social = cambios.get("razon_social", fila["razon_social"])
        nuevo_activo = cambios.get("activo", fila["activo"])
        if not isinstance(nueva_razon_social, str) or not isinstance(nuevo_activo, bool):
            raise EntradaInvalida("razon_social, activo")
        try:
            DatosProveedor(razon_social=nueva_razon_social, cuit=fila["cuit"])
        except ValidationError as error:
            raise error_de_validacion(error) from None
        campos = sorted(
            campo
            for campo, nuevo in (("razon_social", nueva_razon_social), ("activo", nuevo_activo))
            if nuevo != fila[campo]
        )
        if not campos:
            return
        sesion.execute(
            text("UPDATE proveedor SET razon_social=:razon_social, activo=:activo WHERE id=:id"),
            {"razon_social": nueva_razon_social, "activo": nuevo_activo, "id": proveedor_id},
        )
        registrar(
            sesion,
            identidad,
            EventoDelGasto.EDITAR_PROVEEDOR,
            entidad="proveedor",
            entidad_id=proveedor_id,
            request_id=request_id,
            detalle={"complejo_id": str(fila["complejo_id"]), "campos": campos},
        )
