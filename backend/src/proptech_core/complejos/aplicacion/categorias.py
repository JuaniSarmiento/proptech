"""Categorías por edificio, sin borrado y con reordenamiento completo."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.parametros import CategoriaDeGasto
from proptech_core.complejos.aplicacion.errores import (
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.complejos.aplicacion.lectura import cargar_complejo

_CONFLICTOS = {"uq_categoria_clave": "clave", "uq_categoria_nombre": "nombre"}


class _Edicion(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    nombre: str
    activa: bool


def _bloquear_edificio(sesion: Session, complejo_id: UUID) -> None:
    if (
        sesion.execute(
            text("SELECT id FROM complejo WHERE id=:id FOR UPDATE"), {"id": complejo_id}
        ).first()
        is None
    ):
        raise NoEncontrado()


def listar_categorias(
    sesion: Session, complejo_id: UUID, *, solo_activas: bool = False
) -> list[dict[str, Any]]:
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    return [
        dict(f)
        for f in sesion.execute(
            text(
                "SELECT id, complejo_id, clave, nombre, orden, activa FROM categoria_de_gasto "
                "WHERE complejo_id=:id AND (NOT :solo OR activa) ORDER BY orden"
            ),
            {"id": complejo_id, "solo": solo_activas},
        ).mappings()
    ]


def crear_categoria(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, datos: dict[str, Any]
) -> UUID:
    try:
        entrada = CategoriaDeGasto.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None
    with transaccion(sesion, _CONFLICTOS):
        # Serializa el cálculo del siguiente orden con otras altas y reordenamientos.
        _bloquear_edificio(sesion, complejo_id)
        orden = sesion.execute(
            text(
                "SELECT COALESCE(max(orden), -1) + 1 FROM categoria_de_gasto WHERE complejo_id=:id"
            ),
            {"id": complejo_id},
        ).scalar_one()
        categoria_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO categoria_de_gasto (administracion_id, complejo_id, "
                        "clave, nombre, orden) "
                        "VALUES (:admin, :complejo, :clave, :nombre, :orden) RETURNING id"
                    ),
                    {
                        **entrada.model_dump(),
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                        "orden": orden,
                    },
                ).scalar_one()
            )
        )
    return categoria_id


def editar_categoria(sesion: Session, *, categoria_id: UUID, cambios: dict[str, Any]) -> None:
    with transaccion(sesion, _CONFLICTOS):
        fila = (
            sesion.execute(
                text(
                    "SELECT clave, nombre, activa FROM categoria_de_gasto WHERE id=:id FOR UPDATE"
                ),
                {"id": categoria_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        try:
            entrada = _Edicion.model_validate(
                {"nombre": fila["nombre"], "activa": fila["activa"], **cambios}
            )
            CategoriaDeGasto(clave=fila["clave"], nombre=entrada.nombre)
        except ValidationError as error:
            raise error_de_validacion(error) from None
        sesion.execute(
            text("UPDATE categoria_de_gasto SET nombre=:nombre, activa=:activa WHERE id=:id"),
            {**entrada.model_dump(), "id": categoria_id},
        )


def reordenar_categorias(sesion: Session, *, complejo_id: UUID, orden: list[UUID]) -> None:
    with transaccion(sesion, {}):
        _bloquear_edificio(sesion, complejo_id)
        existentes = set(
            sesion.execute(
                text("SELECT id FROM categoria_de_gasto WHERE complejo_id=:id FOR UPDATE"),
                {"id": complejo_id},
            ).scalars()
        )
        if len(orden) != len(set(orden)) or set(orden) != existentes:
            raise EntradaInvalida("orden")
        for posicion, categoria in enumerate(orden):
            sesion.execute(
                text(
                    "UPDATE categoria_de_gasto SET orden=:orden "
                    "WHERE id=:id AND complejo_id=:complejo"
                ),
                {"orden": posicion, "id": categoria, "complejo": complejo_id},
            )
