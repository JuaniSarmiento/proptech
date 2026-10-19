"""Altas y edición del padrón; la sesión ya tiene el tenant y el alcance autorizado."""

from typing import Annotated, Any, TypedDict
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.coeficientes import (
    Coeficiente,
    InformeCoeficientes,
    informar_coeficientes,
)
from proptech_core.compartido.superficie import Superficie
from proptech_core.compartido.texto import recortado_sin_control, sin_caracteres_de_control
from proptech_core.compartido.tipos_de_unidad import TIPOS_DE_UNIDAD_VALIDOS
from proptech_core.complejos.aplicacion.errores import (
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.complejos.aplicacion.lectura import cargar_complejo


class DatosUnidad(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    #: R3A-1/R3A-6: nunca un carácter de control (U+0000 incluido, que
    #: PostgreSQL rechaza crudo), y el identificador se recorta en el borde
    #: para que "1A " no sea otra unidad que "1A".
    identificador: Annotated[
        str, Field(min_length=1, max_length=40), AfterValidator(recortado_sin_control)
    ]
    tipo: str
    piso: Annotated[str, AfterValidator(sin_caracteres_de_control)]
    coeficiente: Coeficiente
    superficie_m2: Superficie

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, valor: str) -> str:
        if valor not in TIPOS_DE_UNIDAD_VALIDOS:
            raise ValueError("tipo desconocido")
        return valor

    @field_validator("superficie_m2")
    @classmethod
    def superficie_positiva(cls, valor: Superficie) -> Superficie:
        if valor.decimal <= 0:
            raise ValueError("debe ser positiva")
        return valor


class Padron(TypedDict):
    unidades: list[dict[str, Any]]
    informe: InformeCoeficientes


def _datos(datos: dict[str, Any]) -> DatosUnidad:
    try:
        return DatosUnidad.model_validate(datos)
    except ValidationError as error:
        raise error_de_validacion(error) from None


def listar_unidades(sesion: Session, complejo_id: UUID) -> Padron:
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    filas = (
        sesion.execute(
            text(
                "SELECT id, complejo_id, identificador, tipo, piso, "
                "coeficiente::text, superficie_m2::text "
                "FROM unidad WHERE complejo_id=:id ORDER BY identificador, id"
            ),
            {"id": complejo_id},
        )
        .mappings()
        .all()
    )
    return {
        "unidades": [dict(f) for f in filas],
        "informe": informar_coeficientes(Coeficiente(f["coeficiente"]) for f in filas),
    }


def crear_unidad(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, datos: dict[str, Any]
) -> UUID:
    entrada = _datos(datos)
    with transaccion(sesion, {"uq_unidad_identificador": "identificador"}):
        if cargar_complejo(sesion, complejo_id) is None:
            raise NoEncontrado()
        unidad_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO unidad (administracion_id, complejo_id, "
                        "identificador, tipo, piso, "
                        "coeficiente, superficie_m2) VALUES (:admin, :complejo, "
                        ":identificador, :tipo, :piso, "
                        ":coeficiente, :superficie_m2) RETURNING id"
                    ),
                    {
                        **entrada.model_dump(mode="json"),
                        "admin": identidad.administracion_id,
                        "complejo": complejo_id,
                    },
                ).scalar_one()
            )
        )
    return unidad_id


def editar_unidad(sesion: Session, *, unidad_id: UUID, cambios: dict[str, Any]) -> None:
    with transaccion(sesion, {"uq_unidad_identificador": "identificador"}):
        fila = (
            sesion.execute(
                text(
                    "SELECT identificador, tipo, piso, coeficiente::text, superficie_m2::text "
                    "FROM unidad WHERE id=:id FOR UPDATE"
                ),
                {"id": unidad_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        entrada = _datos({**fila, **cambios})
        sesion.execute(
            text(
                "UPDATE unidad SET identificador=:identificador, tipo=:tipo, piso=:piso, "
                "coeficiente=:coeficiente, superficie_m2=:superficie_m2 WHERE id=:id"
            ),
            {**entrada.model_dump(mode="json"), "id": unidad_id},
        )
