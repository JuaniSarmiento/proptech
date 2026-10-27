"""Casos de uso de escritura de `complejos` (D7, D9, cambio 2a, tarea 6.2).

`asignar_complejo_a_persona`, marcado con `@accion_sensible`, inserta la
fila de `asignacion_rol` y audita la acción
en la MISMA sesión (D9). El bloque usa `transaccion` para traducir duplicados a `Conflicto` (D6),
con un `SAVEPOINT`
(`sesion.begin_nested()`) si la sesión ya venía con una transacción abierta
— el caso normal de la API, que ya leyó antes de llegar hasta acá — o una
transacción propia (`sesion.begin()`) si no, como en un caso de uso que abre
su propia sesión. Cualquier excepción dentro del bloque revierte las dos
filas (la de `asignacion_rol` y la de `auditoria`, si llegó a escribirse).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.eventos import EventoDelPadron
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.georef import Georef
from proptech_core.compartido.parametros import Parametros
from proptech_core.compartido.pisos import vocabulario_de_pisos
from proptech_core.compartido.texto import recortado_sin_control
from proptech_core.complejos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    error_de_validacion,
    transaccion,
)
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.complejos.dominio.configuracion import ConfiguracionEdificio

_ACCION = Accion.INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS


@accion_sensible(_ACCION)
def asignar_complejo_a_persona(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    persona_id: UUID,
    rol: str,
    request_id: UUID,
) -> UUID:
    with transaccion(
        sesion,
        {
            "uq_asignacion_rol_persona_alcance": "rol",
            "uq_asignacion_rol_consejo_persona_complejo": "rol",
        },
    ):
        fila = sesion.execute(
            text(
                "INSERT INTO asignacion_rol "
                "(administracion_id, persona_id, rol, complejo_id) "
                "VALUES (:administracion_id, :persona_id, :rol, :complejo_id) "
                "RETURNING id"
            ),
            {
                # Siempre de la identidad (D7): nunca de un campo del pedido.
                "administracion_id": str(identidad.administracion_id),
                "persona_id": str(persona_id),
                "rol": rol,
                "complejo_id": str(complejo_id),
            },
        ).one()
        registrar(
            sesion,
            identidad,
            _ACCION,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "rol": rol,
                "alcance": "edificio",
                "persona_id": str(persona_id),
                "asignacion_id": str(fila.id),
            },
        )
    # psycopg3 ya devuelve una columna uuid como `uuid.UUID`, incluso en un
    # `text()` crudo; el `str()`/`UUID()` sólo blinda el tipo para mypy.
    return UUID(str(fila.id))


def hoy_en_mendoza(reloj: Callable[[], datetime]) -> date:
    instante = reloj()
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ValueError("el reloj debe devolver un instante con zona horaria")
    return instante.astimezone(ZoneInfo("America/Argentina/Mendoza")).date()


def insertar_configuracion(
    sesion: Session,
    identidad: Identidad,
    complejo_id: UUID,
    vigente_desde: date,
    configuracion: ConfiguracionEdificio,
) -> UUID:
    valores = configuracion.model_dump(mode="json")
    return UUID(
        str(
            sesion.execute(
                text(
                    "INSERT INTO configuracion_versionada "
                    "(administracion_id, complejo_id, vigente_desde, "
                    "autor_id, tasa_mensual, dias_de_gracia, forma_de_calculo, porcentaje_fondo, "
                    "dia_de_vencimiento, modalidad_de_vencimiento, dia_segundo_vencimiento, "
                    "recargo_segundo_vencimiento, umbral_saldo_chico) VALUES (:admin, "
                    ":complejo, :fecha, :autor, :tasa_mensual, "
                    ":dias_de_gracia, :forma_de_calculo, :porcentaje_fondo, :dia_de_vencimiento, "
                    ":modalidad_de_vencimiento, "
                    ":dia_segundo_vencimiento, :recargo_segundo_vencimiento, :umbral_saldo_chico) "
                    "RETURNING id"
                ),
                {
                    **valores,
                    "admin": identidad.administracion_id,
                    "complejo": complejo_id,
                    "fecha": vigente_desde,
                    "autor": identidad.persona_id,
                },
            ).scalar_one()
        )
    )


@accion_sensible(Accion.CREAR_EDIFICIO)
def crear_edificio(
    sesion: Session,
    identidad: Identidad,
    *,
    nombre: str,
    provincia_id: str,
    departamento_id: str,
    localidad_id: str,
    georef: Georef,
    pisos: int,
    subsuelos: int,
    calle_y_numero: str | None = None,
    parametros: Parametros,
    reloj: Callable[[], datetime],
    request_id: UUID,
    configuracion_inicial: ConfiguracionEdificio | None = None,
) -> UUID:
    """D2/D1 (tarea 2.6): `localidad` deja de ser un parámetro — la
    aplicación es la única autoridad sobre la ubicación, contra el archivo
    de Georef, nunca contra lo que mande el cliente. `campo_incoherente`
    nombra el primer campo que no encadena (provincia → departamento →
    localidad); `localidad` se escribe siempre derivada del nombre real de
    Georef, nunca de un valor del pedido.

    D3 (tarea 3.2): un edificio nuevo trae `pisos` (1 a 60) y `subsuelos`
    (0 a 5) siempre — nunca `None` acá, aunque la columna sea nullable para
    los edificios migrados sin completar (D3). El rango se valida acá
    también (no sólo en el `Field` del cuerpo de la API) para que un
    llamador que no pase por HTTP (`ejemplo.py`, los tests) no pueda
    escaparse del límite."""
    campo_invalido = georef.campo_incoherente(provincia_id, departamento_id, localidad_id)
    if campo_invalido is not None:
        raise EntradaInvalida(campo_invalido)
    localidad = georef.nombre_de_localidad(localidad_id)
    if localidad is None:
        # No alcanzable en los hechos: `campo_incoherente` ya confirmó que
        # `localidad_id` existe. Nunca `assert` en código de producción
        # (S101): se cae a un error explícito en vez de silenciarlo con -O.
        raise RuntimeError("localidad inexistente pese a pasar la validación de coherencia")
    if not (1 <= pisos <= 60):
        raise EntradaInvalida("pisos", "debe estar entre 1 y 60")
    if not (0 <= subsuelos <= 5):
        raise EntradaInvalida("subsuelos", "debe estar entre 0 y 5")
    configuracion = configuracion_inicial or ConfiguracionEdificio.desde_parametros(parametros)
    configuracion.validar_rango_recargo(parametros)
    if configuracion.umbral_saldo_chico is None:
        configuracion = configuracion.model_copy(
            update={"umbral_saldo_chico": parametros.cuenta_corriente.umbral_saldo_chico}
        )
    hoy = hoy_en_mendoza(reloj)
    # R3A-2 (L-018): `leer_parametros` ya rechaza nombres de categoría
    # repetidos sin distinguir mayúsculas al arranque; este `transaccion`
    # es la segunda capa, para que un `parametros.yaml` que se le escape a
    # esa validación (o un futuro caller que no pase por `leer_parametros`)
    # no vuelva a dejar escapar la `UniqueViolation` cruda (500).
    with transaccion(sesion, {"uq_categoria_nombre": "categorias_de_gasto"}):
        complejo_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO complejo (administracion_id, nombre, localidad, "
                        "provincia_id, departamento_id, localidad_id, calle_y_numero, "
                        "pisos, subsuelos, estado_migracion) "
                        "VALUES (:admin, :nombre, :localidad, :provincia_id, "
                        ":departamento_id, :localidad_id, :calle_y_numero, :pisos, "
                        ":subsuelos, 'pendiente') "
                        "RETURNING id"
                    ),
                    {
                        "admin": identidad.administracion_id,
                        "nombre": nombre,
                        "localidad": localidad,
                        "provincia_id": provincia_id,
                        "departamento_id": departamento_id,
                        "localidad_id": localidad_id,
                        "calle_y_numero": calle_y_numero,
                        "pisos": pisos,
                        "subsuelos": subsuelos,
                    },
                ).scalar_one()
            )
        )
        insertar_configuracion(sesion, identidad, complejo_id, hoy, configuracion)
        for orden, categoria in enumerate(parametros.categorias_de_gasto):
            sesion.execute(
                text(
                    "INSERT INTO categoria_de_gasto "
                    "(administracion_id, complejo_id, clave, nombre, "
                    "orden) VALUES (:admin, :complejo, :clave, :nombre, :orden)"
                ),
                {
                    "admin": identidad.administracion_id,
                    "complejo": complejo_id,
                    "clave": categoria.clave,
                    "nombre": categoria.nombre,
                    "orden": orden,
                },
            )
        sesion.execute(
            text(
                "INSERT INTO grupo_de_reparto (administracion_id, "
                "complejo_id, clave, nombre, metodo, "
                "es_generales) VALUES (:admin, :complejo, 'generales', 'Generales', "
                "'coeficiente', true)"
            ),
            {"admin": identidad.administracion_id, "complejo": complejo_id},
        )
        registrar(
            sesion,
            identidad,
            Accion.CREAR_EDIFICIO,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id)},
        )
    return complejo_id


@accion_sensible(Accion.CREAR_VERSION_DE_CONFIGURACION)
def crear_version_de_configuracion(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    configuracion: ConfiguracionEdificio,
    vigente_desde: date,
    parametros: Parametros,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> UUID:
    if vigente_desde < hoy_en_mendoza(reloj):
        raise EntradaInvalida("vigente_desde", "no puede ser anterior a hoy en Mendoza")
    try:
        configuracion.validar_rango_recargo(parametros)
    except ValueError:
        raise EntradaInvalida(
            "recargo_segundo_vencimiento", "fuera del rango de parámetros"
        ) from None
    with transaccion(sesion, {"uq_configuracion_vigencia": "vigente_desde"}):
        if cargar_complejo(sesion, complejo_id) is None:
            raise NoEncontrado()
        if configuracion.umbral_saldo_chico is None:
            anterior = sesion.execute(
                text(
                    "SELECT umbral_saldo_chico FROM configuracion_versionada "
                    "WHERE administracion_id=:admin AND complejo_id=:complejo "
                    "AND vigente_desde<:fecha ORDER BY vigente_desde DESC LIMIT 1"
                ),
                {
                    "admin": identidad.administracion_id,
                    "complejo": complejo_id,
                    "fecha": vigente_desde,
                },
            ).scalar_one_or_none()
            from proptech_core.compartido.dinero import Dinero

            umbral = (
                parametros.cuenta_corriente.umbral_saldo_chico
                if anterior is None
                else Dinero.desde_decimal(anterior)
            )
            configuracion = configuracion.model_copy(update={"umbral_saldo_chico": umbral})
        version_id = insertar_configuracion(
            sesion, identidad, complejo_id, vigente_desde, configuracion
        )
        registrar(
            sesion,
            identidad,
            Accion.CREAR_VERSION_DE_CONFIGURACION,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id), "vigente_desde": vigente_desde.isoformat()},
        )
    return version_id


@accion_sensible(Accion.CONFIRMAR_SIN_SALDOS_PREVIOS)
def confirmar_sin_saldos_previos(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, request_id: UUID
) -> UUID:
    with transaccion(sesion, {}):
        estado = sesion.execute(
            text("SELECT estado_migracion FROM complejo WHERE id=:id FOR UPDATE"),
            {"id": complejo_id},
        ).scalar_one_or_none()
        if estado is None:
            raise NoEncontrado()
        if estado != "pendiente":
            raise Conflicto("estado_migracion")
        sesion.execute(
            text("UPDATE complejo SET estado_migracion='sin_saldos_previos' WHERE id=:id"),
            {"id": complejo_id},
        )
        registrar(
            sesion,
            identidad,
            Accion.CONFIRMAR_SIN_SALDOS_PREVIOS,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id)},
        )
    return complejo_id


class _EdicionEdificio(BaseModel):
    """D3/D2 (tareas 3.5-3.7): los mismos campos editables de `complejo`,
    todos nullable (`None` es "sin completar", igual que en el alta) — el
    `CuerpoDeEdicion` de la API ya prohíbe mandar `null` explícito; este
    modelo sólo valida FORMA, nunca el trío de ubicación entre sí (eso lo
    hace `editar_edificio` con `Georef`, que esta clase no conoce)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    nombre: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(recortado_sin_control)
    ]
    provincia_id: str | None
    departamento_id: str | None
    localidad_id: str | None
    calle_y_numero: (
        Annotated[str, Field(max_length=200), AfterValidator(recortado_sin_control)] | None
    )
    pisos: Annotated[int, Field(ge=1, le=60)] | None
    subsuelos: Annotated[int, Field(ge=0, le=5)] | None


@accion_sensible(EventoDelPadron.EDITAR_EDIFICIO)
def editar_edificio(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    cambios: dict[str, Any],
    georef: Georef,
    request_id: UUID,
) -> None:
    """D3 (tareas 3.5-3.7): nombre, ubicación, calle y número, pisos y
    subsuelos. El trío de ubicación se valida completo o ninguno (mismo
    `CHECK` que `0025`); bajar `pisos`/`subsuelos` se rechaza si deja
    alguna unidad en un piso que el edificio ya no tiene (D3, tarea 3.5),
    nombrando sus identificadores — no son un valor del PEDIDO (L-007), son
    datos propios del edificio que el mismo administrador ya puede ver."""
    with transaccion(sesion, {}):
        fila = (
            sesion.execute(
                text(
                    "SELECT nombre, provincia_id, departamento_id, localidad_id, "
                    "calle_y_numero, pisos, subsuelos FROM complejo WHERE id=:id FOR UPDATE"
                ),
                {"id": complejo_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise NoEncontrado()
        try:
            anterior = _EdicionEdificio.model_validate(dict(fila))
            entrada = _EdicionEdificio.model_validate({**fila, **cambios})
        except ValidationError as error:
            raise error_de_validacion(error) from None
        campos = sorted(
            k for k in type(entrada).model_fields if getattr(entrada, k) != getattr(anterior, k)
        )
        if not campos:
            return
        provincia_id, departamento_id, localidad_id = (
            entrada.provincia_id,
            entrada.departamento_id,
            entrada.localidad_id,
        )
        localidad: str | None = None
        if provincia_id is not None or departamento_id is not None or localidad_id is not None:
            if provincia_id is None:
                raise EntradaInvalida("provincia_id", "la ubicación exige el trío completo")
            if departamento_id is None:
                raise EntradaInvalida("departamento_id", "la ubicación exige el trío completo")
            if localidad_id is None:
                raise EntradaInvalida("localidad_id", "la ubicación exige el trío completo")
            campo_invalido = georef.campo_incoherente(provincia_id, departamento_id, localidad_id)
            if campo_invalido is not None:
                raise EntradaInvalida(campo_invalido)
            localidad = georef.nombre_de_localidad(localidad_id)
        if (
            entrada.pisos is not None
            and entrada.subsuelos is not None
            and ("pisos" in campos or "subsuelos" in campos)
        ):
            vocabulario = vocabulario_de_pisos(pisos=entrada.pisos, subsuelos=entrada.subsuelos)
            unidades_del_edificio = sesion.execute(
                text(
                    "SELECT identificador, piso FROM unidad "
                    "WHERE complejo_id=:id AND piso IS NOT NULL"
                ),
                {"id": complejo_id},
            ).all()
            fuera_de_rango = sorted(
                identificador
                for identificador, piso in unidades_del_edificio
                if piso not in vocabulario
            )
            if fuera_de_rango:
                campo = "pisos" if "pisos" in campos else "subsuelos"
                raise EntradaInvalida(
                    campo,
                    "quedarían unidades fuera de rango: " + ", ".join(fuera_de_rango),
                    tipo="fuera_de_rango",
                    identificadores=fuera_de_rango,
                )
        sesion.execute(
            text(
                "UPDATE complejo SET nombre=:nombre, provincia_id=:provincia_id, "
                "departamento_id=:departamento_id, localidad_id=:localidad_id, "
                "localidad=:localidad, calle_y_numero=:calle_y_numero, "
                "pisos=:pisos, subsuelos=:subsuelos WHERE id=:id"
            ),
            {**entrada.model_dump(), "localidad": localidad, "id": complejo_id},
        )
        registrar(
            sesion,
            identidad,
            EventoDelPadron.EDITAR_EDIFICIO,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id), "campos": campos},
        )
