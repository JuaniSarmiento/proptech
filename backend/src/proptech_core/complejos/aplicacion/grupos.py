"""Grupos del edificio y reemplazo atómico de sus miembros (D6, D15)."""

import re
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.coeficientes import Coeficiente, informar_coeficientes
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.complejos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.complejos.aplicacion.lectura import cargar_complejo

_CONFLICTOS = {"uq_grupo_clave": "clave", "uq_grupo_unidad": "unidades"}


class DatosGrupo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    clave: str
    #: R3A-1/R3A-6: nunca un carácter de control, recortado en el borde.
    nombre: Annotated[
        str, Field(min_length=1, max_length=80), AfterValidator(recortado_sin_control)
    ]
    metodo: Literal["coeficiente", "superficie", "partes_iguales"]

    @field_validator("clave")
    @classmethod
    def clave_valida(cls, valor: str) -> str:
        if re.fullmatch(r"[a-z][a-z0-9_]{0,39}", valor, re.ASCII) is None:
            raise ValueError("clave inválida")
        return valor


class Miembro(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    unidad_id: UUID
    coeficiente: Coeficiente | None = None


def _grupo(sesion: Session, grupo_id: UUID) -> dict[str, Any]:
    fila = (
        sesion.execute(
            text("SELECT * FROM grupo_de_reparto WHERE id=:id FOR UPDATE"), {"id": grupo_id}
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise NoEncontrado()
    return dict(fila)


def listar_grupos(sesion: Session, complejo_id: UUID) -> list[dict[str, Any]]:
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    grupos = (
        sesion.execute(
            text(
                "SELECT * FROM grupo_de_reparto WHERE complejo_id=:id "
                "ORDER BY es_generales DESC, clave"
            ),
            {"id": complejo_id},
        )
        .mappings()
        .all()
    )
    generales = [
        dict(f)
        for f in sesion.execute(
            text(
                "SELECT id AS unidad_id, coeficiente::text FROM unidad "
                "WHERE complejo_id=:id ORDER BY id"
            ),
            {"id": complejo_id},
        ).mappings()
    ]
    miembros: dict[UUID, list[dict[str, Any]]] = {}
    for fila in sesion.execute(
        text(
            "SELECT grupo_id, unidad_id, coeficiente::text FROM grupo_unidad "
            "WHERE complejo_id=:id ORDER BY unidad_id"
        ),
        {"id": complejo_id},
    ).mappings():
        miembros.setdefault(fila["grupo_id"], []).append(
            {
                "unidad_id": fila["unidad_id"],
                "coeficiente": fila["coeficiente"],
            }
        )
    resultado = []
    for grupo in grupos:
        if grupo["es_generales"]:
            unidades = generales
        else:
            unidades = miembros.get(grupo["id"], [])
        propio = grupo["es_generales"] or grupo["modo_de_coeficientes"] == "propios"
        informe = (
            informar_coeficientes(Coeficiente(u["coeficiente"]) for u in unidades)
            if propio
            else None
        )
        resultado.append({**grupo, "unidades": unidades, "informe": informe})
    return resultado


def _reemplazar(
    sesion: Session, grupo: dict[str, Any], modo: str, miembros: list[dict[str, Any]]
) -> None:
    if grupo["es_generales"]:
        raise EntradaInvalida("unidades", "Generales es inmutable")
    if modo not in ("renormalizado", "propios") or (
        modo == "propios" and grupo["metodo"] != "coeficiente"
    ):
        raise EntradaInvalida("modo_de_coeficientes")
    try:
        entradas = [Miembro.model_validate(m) for m in miembros]
    except ValidationError as error:
        raise error_de_validacion(error) from None
    ids = [m.unidad_id for m in entradas]
    if len(ids) != len(set(ids)):
        raise Conflicto("unidades")
    if any((modo == "propios") != (m.coeficiente is not None) for m in entradas):
        raise EntradaInvalida("unidades")
    encontrados = set(
        sesion.execute(
            text("SELECT id FROM unidad WHERE complejo_id=:complejo AND id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"complejo": grupo["complejo_id"], "ids": ids},
        ).scalars()
    )
    if encontrados != set(ids):
        raise EntradaInvalida("unidades")
    # El CHECK de los miembros no es diferible: borrar antes del cambio de modo (D15).
    sesion.execute(text("DELETE FROM grupo_unidad WHERE grupo_id=:id"), {"id": grupo["id"]})
    sesion.execute(
        text("UPDATE grupo_de_reparto SET modo_de_coeficientes=:modo WHERE id=:id"),
        {"modo": modo, "id": grupo["id"]},
    )
    for miembro in entradas:
        sesion.execute(
            text(
                "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id, "
                "modo_de_coeficientes, coeficiente) VALUES (:admin, :complejo, :grupo, :unidad, "
                ":modo, :coeficiente)"
            ),
            {
                "admin": grupo["administracion_id"],
                "complejo": grupo["complejo_id"],
                "grupo": grupo["id"],
                "unidad": miembro.unidad_id,
                "modo": modo,
                "coeficiente": None
                if miembro.coeficiente is None
                else miembro.coeficiente.a_texto(),
            },
        )


def crear_grupo(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    datos: dict[str, Any],
    miembros: list[dict[str, Any]],
    modo: str = "renormalizado",
) -> UUID:
    try:
        entrada = DatosGrupo.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None
    with transaccion(sesion, _CONFLICTOS):
        if cargar_complejo(sesion, complejo_id) is None:
            raise NoEncontrado()
        grupo_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO grupo_de_reparto "
                        "(administracion_id, complejo_id, clave, nombre, metodo) "
                        "VALUES (:admin, :complejo, :clave, :nombre, :metodo) RETURNING id"
                    ),
                    {
                        **entrada.model_dump(),
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                    },
                ).scalar_one()
            )
        )
        _reemplazar(sesion, _grupo(sesion, grupo_id), modo, miembros)
    return grupo_id


def editar_grupo(sesion: Session, *, grupo_id: UUID, cambios: dict[str, Any]) -> None:
    with transaccion(sesion, _CONFLICTOS):
        grupo = _grupo(sesion, grupo_id)
        if grupo["es_generales"]:
            raise EntradaInvalida("grupo", "Generales es inmutable")
        try:
            entrada = DatosGrupo.model_validate(
                {
                    **{k: grupo[k] for k in ("clave", "nombre", "metodo")},
                    **cambios,
                }
            )
        except ValidationError as error:
            raise error_de_validacion(error) from None
        if grupo["modo_de_coeficientes"] == "propios" and entrada.metodo != "coeficiente":
            raise EntradaInvalida("metodo")
        sesion.execute(
            text(
                "UPDATE grupo_de_reparto SET clave=:clave, "
                "nombre=:nombre, metodo=:metodo WHERE id=:id"
            ),
            {**entrada.model_dump(), "id": grupo_id},
        )


def fijar_unidades(
    sesion: Session, *, grupo_id: UUID, modo: str, miembros: list[dict[str, Any]]
) -> None:
    with transaccion(sesion, _CONFLICTOS):
        _reemplazar(sesion, _grupo(sesion, grupo_id), modo, miembros)
