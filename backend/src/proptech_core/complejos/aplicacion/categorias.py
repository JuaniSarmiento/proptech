"""Categorías por edificio, sin borrado y con reordenamiento completo."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.eventos import EventoDelPadron
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.claves import derivar_clave
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
    #: D7 (tarea 4.4): sin `clave` (o `None`), se deriva de `nombre` contra
    #: las que el edificio ya tiene — `CategoriaDeGasto` sigue exigiendo
    #: `clave` siempre (la usa también el YAML de parámetros, D-042), así
    #: que la derivación pasa ANTES de validar con ella, nunca dentro.
    if not datos.get("clave"):
        nombre = datos.get("nombre")
        existentes = (
            sesion.execute(
                text("SELECT clave FROM categoria_de_gasto WHERE complejo_id=:id"),
                {"id": complejo_id},
            )
            .scalars()
            .all()
        )
        clave_derivada = derivar_clave(nombre, existentes) if isinstance(nombre, str) else None
        if clave_derivada is None:
            raise EntradaInvalida("nombre", "no se puede derivar una clave")
        datos = {**datos, "clave": clave_derivada}
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


@accion_sensible(EventoDelPadron.EDITAR_CATEGORIA)
def editar_categoria(
    sesion: Session,
    identidad: Identidad,
    *,
    categoria_id: UUID,
    cambios: dict[str, Any],
    request_id: UUID,
) -> None:
    with transaccion(sesion, _CONFLICTOS):
        fila = (
            sesion.execute(
                text(
                    "SELECT complejo_id, clave, nombre, activa FROM categoria_de_gasto "
                    "WHERE id=:id FOR UPDATE"
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
        campos = sorted(k for k, v in entrada.model_dump().items() if v != fila[k])
        if not campos:
            return
        sesion.execute(
            text("UPDATE categoria_de_gasto SET nombre=:nombre, activa=:activa WHERE id=:id"),
            {**entrada.model_dump(), "id": categoria_id},
        )

        registrar(
            sesion,
            identidad,
            EventoDelPadron.EDITAR_CATEGORIA,
            entidad="categoria_de_gasto",
            entidad_id=categoria_id,
            request_id=request_id,
            detalle={"complejo_id": str(fila["complejo_id"]), "campos": campos},
        )


@accion_sensible(EventoDelPadron.REORDENAR_CATEGORIAS)
def reordenar_categorias(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, orden: list[UUID], request_id: UUID
) -> None:
    with transaccion(sesion, {}):
        _bloquear_edificio(sesion, complejo_id)
        anteriores = list(
            sesion.execute(
                text(
                    "SELECT id FROM categoria_de_gasto "
                    "WHERE complejo_id=:id ORDER BY orden FOR UPDATE"
                ),
                {"id": complejo_id},
            ).scalars()
        )
        if len(orden) != len(set(orden)) or set(orden) != set(anteriores):
            raise EntradaInvalida("orden")
        if orden == anteriores:
            return
        for posicion, categoria in enumerate(orden):
            sesion.execute(
                text(
                    "UPDATE categoria_de_gasto SET orden=:orden "
                    "WHERE id=:id AND complejo_id=:complejo"
                ),
                {"orden": posicion, "id": categoria, "complejo": complejo_id},
            )

        registrar(
            sesion,
            identidad,
            EventoDelPadron.REORDENAR_CATEGORIAS,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id), "campos": ["orden"]},
        )
