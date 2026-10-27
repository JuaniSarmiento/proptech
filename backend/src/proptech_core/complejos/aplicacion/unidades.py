"""Altas y edición del padrón; la sesión ya tiene el tenant y el alcance autorizado."""

from typing import Annotated, Any, TypedDict
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.eventos import EventoDelPadron
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.coeficientes import (
    Coeficiente,
    InformeCoeficientes,
    informar_coeficientes,
)
from proptech_core.compartido.pisos import PATRON_PISO, piso_valido
from proptech_core.compartido.superficie import Superficie
from proptech_core.compartido.texto import recortado_sin_control, sin_caracteres_de_control
from proptech_core.compartido.tipos_de_unidad import TIPOS_DE_UNIDAD_VALIDOS
from proptech_core.complejos.aplicacion.errores import (
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.complejos.aplicacion.lectura import ComplejoLeido, cargar_complejo


class DatosUnidad(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    #: R3A-1/R3A-6: nunca un carácter de control (U+0000 incluido, que
    #: PostgreSQL rechaza crudo), y el identificador se recorta en el borde
    #: para que "1A " no sea otra unidad que "1A".
    identificador: Annotated[
        str, Field(min_length=1, max_length=40), AfterValidator(recortado_sin_control)
    ]
    tipo: str
    #: Nullable (D3, tarea 3.3): una unidad migrada puede tener el piso sin
    #: completar (`None`); un alta nueva lo exige (chequeo explícito en
    #: `crear_unidad`, no acá, porque este tipo también lee filas existentes
    #: con el piso ya en `None`). El validador sólo chequea la FORMA
    #: (`PATRON_PISO`, lo que el `CHECK ck_unidad_piso` de `0024` puede
    #: expresar); el vocabulario DEL EDIFICIO (D3, `pisos`/`subsuelos`) se
    #: valida en `crear_unidad`/`editar_unidad`, que conocen el edificio.
    piso: str | None
    coeficiente: Coeficiente
    superficie_m2: Superficie

    @field_validator("piso")
    @classmethod
    def piso_con_forma(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = sin_caracteres_de_control(valor)
        if not PATRON_PISO.fullmatch(valor):
            raise ValueError("no coincide con el vocabulario de pisos")
        return valor

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


def _validar_piso_del_edificio(
    piso: str | None, complejo: ComplejoLeido, *, requerido: bool
) -> None:
    """D3 (tarea 3.3): el `CHECK ck_unidad_piso` de `0024` sólo valida la
    FORMA (lo que la base puede expresar); acá se valida que el piso esté
    DENTRO del vocabulario de ESTE edificio en particular. Un edificio
    migrado sin `pisos`/`subsuelos` completados (D3) todavía no tiene
    vocabulario propio — se deja pasar lo que ya pasó la forma, hasta que
    se complete (tarea 3.8)."""
    if piso is None:
        if requerido:
            raise EntradaInvalida("piso", "requerido")
        return
    if complejo.pisos is None or complejo.subsuelos is None:
        return
    if not piso_valido(piso, pisos=complejo.pisos, subsuelos=complejo.subsuelos):
        raise EntradaInvalida("piso", "no está entre los pisos del edificio")


@accion_sensible(EventoDelPadron.CREAR_UNIDAD)
def crear_unidad(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    datos: dict[str, Any],
    request_id: UUID,
) -> UUID:
    entrada = _datos(datos)
    with transaccion(sesion, {"uq_unidad_identificador": "identificador"}):
        complejo = cargar_complejo(sesion, complejo_id)
        if complejo is None:
            raise NoEncontrado()
        _validar_piso_del_edificio(entrada.piso, complejo, requerido=True)
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
        registrar(
            sesion,
            identidad,
            EventoDelPadron.CREAR_UNIDAD,
            entidad="unidad",
            entidad_id=unidad_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "campos": sorted(type(entrada).model_fields),
                "coeficiente": {"anterior": None, "nuevo": entrada.coeficiente.a_texto()},
            },
        )
    return unidad_id


@accion_sensible(EventoDelPadron.EDITAR_UNIDAD)
def editar_unidad(
    sesion: Session,
    identidad: Identidad,
    *,
    unidad_id: UUID,
    cambios: dict[str, Any],
    request_id: UUID,
) -> None:
    with transaccion(sesion, {"uq_unidad_identificador": "identificador"}):
        fila = (
            sesion.execute(
                text(
                    "SELECT complejo_id, identificador, tipo, piso, "
                    "coeficiente::text, superficie_m2::text "
                    "FROM unidad WHERE id=:id FOR UPDATE"
                ),
                {"id": unidad_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        anterior = _datos({k: v for k, v in fila.items() if k != "complejo_id"})
        entrada = _datos({**anterior.model_dump(), **cambios})
        campos = sorted(
            k for k in type(entrada).model_fields if getattr(entrada, k) != getattr(anterior, k)
        )
        if not campos:
            return
        if "piso" in campos:
            complejo = cargar_complejo(sesion, fila["complejo_id"])
            if complejo is None:
                raise NoEncontrado()
            _validar_piso_del_edificio(entrada.piso, complejo, requerido=False)
        detalle: dict[str, Any] = {"complejo_id": str(fila["complejo_id"]), "campos": campos}
        if "coeficiente" in campos:
            detalle["coeficiente"] = {
                "anterior": anterior.coeficiente.a_texto(),
                "nuevo": entrada.coeficiente.a_texto(),
            }
        sesion.execute(
            text(
                "UPDATE unidad SET identificador=:identificador, tipo=:tipo, piso=:piso, "
                "coeficiente=:coeficiente, superficie_m2=:superficie_m2 WHERE id=:id"
            ),
            {**entrada.model_dump(mode="json"), "id": unidad_id},
        )
        registrar(
            sesion,
            identidad,
            EventoDelPadron.EDITAR_UNIDAD,
            entidad="unidad",
            entidad_id=unidad_id,
            request_id=request_id,
            detalle=detalle,
        )
