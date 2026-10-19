"""Casos de uso de escritura de `complejos` (D7, D9, cambio 2a, tarea 6.2).

`asignar_complejo_a_persona` es el único hoy, y el único marcado con
`@accion_sensible`: inserta la fila de `asignacion_rol` y audita la acción
en la MISMA sesión (D9). El bloque usa un `SAVEPOINT`
(`sesion.begin_nested()`) si la sesión ya venía con una transacción abierta
— el caso normal de la API, que ya leyó antes de llegar hasta acá — o una
transacción propia (`sesion.begin()`) si no, como en un caso de uso que abre
su propia sesión. Cualquier excepción dentro del bloque revierte las dos
filas (la de `asignacion_rol` y la de `auditoria`, si llegó a escribirse).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion
from proptech_core.compartido.parametros import Parametros
from proptech_core.complejos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
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
    nivel: str | None,
    request_id: UUID,
) -> UUID:
    bloque = sesion.begin_nested() if sesion.in_transaction() else sesion.begin()
    with bloque:
        fila = sesion.execute(
            text(
                "INSERT INTO asignacion_rol "
                "(administracion_id, persona_id, rol, complejo_id, nivel) "
                "VALUES (:administracion_id, :persona_id, :rol, :complejo_id, :nivel) "
                "RETURNING id"
            ),
            {
                # Siempre de la identidad (D7): nunca de un campo del pedido.
                "administracion_id": str(identidad.administracion_id),
                "persona_id": str(persona_id),
                "rol": rol,
                "complejo_id": str(complejo_id),
                "nivel": nivel,
            },
        ).one()
        registrar(
            sesion,
            identidad,
            _ACCION,
            entidad="complejo",
            entidad_id=complejo_id,
            request_id=request_id,
            detalle={"complejo_id": str(complejo_id)},
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
                    "recargo_segundo_vencimiento) VALUES (:admin, "
                    ":complejo, :fecha, :autor, :tasa_mensual, "
                    ":dias_de_gracia, :forma_de_calculo, :porcentaje_fondo, :dia_de_vencimiento, "
                    ":modalidad_de_vencimiento, "
                    ":dia_segundo_vencimiento, :recargo_segundo_vencimiento) "
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
    localidad: str,
    parametros: Parametros,
    reloj: Callable[[], datetime],
    request_id: UUID,
    configuracion_inicial: ConfiguracionEdificio | None = None,
) -> UUID:
    configuracion = configuracion_inicial or ConfiguracionEdificio.desde_parametros(parametros)
    configuracion.validar_rango_recargo(parametros)
    hoy = hoy_en_mendoza(reloj)
    with sesion.begin_nested() if sesion.in_transaction() else sesion.begin():
        complejo_id = UUID(
            str(
                sesion.execute(
                    text(
                        "INSERT INTO complejo (administracion_id, "
                        "nombre, localidad, estado_migracion) "
                        "VALUES (:admin, :nombre, :localidad, 'pendiente') RETURNING id"
                    ),
                    {
                        "admin": identidad.administracion_id,
                        "nombre": nombre,
                        "localidad": localidad,
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
