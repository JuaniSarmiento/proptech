"""El caso de uso `importar` (design D4, D5, D7 y E3 a E8, E15): sube la plantilla de Excel de
un edificio. Orquesta `acceso` y `complejos` por su `aplicacion`; escribe sólo su propia tabla
(`importacion`) y deja el resto a los casos de uso de esos módulos.

Todo en la misma transacción y todo o nada: cualquier rechazo (de permiso, de estado, de archivo o
de fila) se levanta antes de la primera escritura o la deshace entera.

Orden (D7): edificio o alcance (404) → permiso (403) → fecha de migración (422) → candado del
complejo (`FOR UPDATE`, E8) → estado de migración (409) → huella (409) → lectura del archivo (422)
→ padrón (una sola lectura, D1) y su validación (422) → escritura → auditoría.

H-008 agrega al paso de escritura el borrador de `Saldos` y `Control` (el resto de los pasos no
cambia): `filas_de_saldo` es 0 mientras tanto.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import accion_sensible, registrar
from proptech_core.acceso.aplicacion.autorizacion import cargar_asignaciones
from proptech_core.acceso.aplicacion.propietarios import (
    asegurar_persona,
    asignar_propietario,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import Accion, alcanza, puede
from proptech_core.compartido.pisos import vocabulario_de_pisos
from proptech_core.complejos.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    transaccion,
)
from proptech_core.complejos.aplicacion.escritura import hoy_en_mendoza
from proptech_core.complejos.aplicacion.lectura import ComplejoLeido, cargar_complejo
from proptech_core.complejos.aplicacion.unidades import crear_unidad, listar_unidades
from proptech_core.importacion.aplicacion.errores import ArchivoYaImportado, SinPermiso
from proptech_core.importacion.dominio.padron import (
    ContextoDelEdificio,
    PadronValidado,
    validar_padron,
)
from proptech_core.importacion.dominio.plantilla import ErrorDeImportacion
from proptech_core.importacion.dominio.propietarios import agrupar_propietarios
from proptech_core.importacion.puertos import LectorDePlantilla

_LARGO_DEL_NOMBRE = 255


@dataclass(frozen=True)
class ResultadoDeImportacion:
    importacion_id: UUID
    unidades_creadas: int
    #: Personas nuevas en la administración.
    propietarios_creados: int
    #: Personas que ya existían en la administración antes de importar (repetir un email dentro del
    #: archivo no cuenta).
    propietarios_reusados: int
    filas_de_saldo: int
    advertencias: tuple[ErrorDeImportacion, ...]


def _nombre_del_archivo(nombre: str | None) -> str:
    """Sólo el nombre (sin carpetas), imprimible y de largo acotado (lo exige `archivo`)."""
    sin_carpeta = (nombre or "").replace("\\", "/").rsplit("/", 1)[-1]
    limpio = "".join(c for c in sin_carpeta if c.isprintable()).strip()[:_LARGO_DEL_NOMBRE]
    return limpio or "sin nombre"


def _edificio_autorizado(sesion: Session, identidad: Identidad, complejo_id: UUID) -> ComplejoLeido:
    """D7: inexistente, de otra administración o fuera de alcance → `NoEncontrado`; sin el permiso
    → `SinPermiso`. El tenant de la sesión (RLS) ya filtró la otra administración; se vuelve a
    mirar."""
    edificio = cargar_complejo(sesion, complejo_id)
    asignaciones = cargar_asignaciones(sesion, identidad.persona_id)
    if (
        edificio is None
        or edificio.administracion_id != identidad.administracion_id
        or not alcanza(asignaciones, complejo_id)
    ):
        raise NoEncontrado()
    if not puede(asignaciones, Accion.IMPORTAR_PADRON_Y_SALDOS, complejo_id):
        raise SinPermiso(Accion.IMPORTAR_PADRON_Y_SALDOS.value)
    return edificio


def _importacion_vigente_con_la_huella(
    sesion: Session, complejo_id: UUID, huella: str
) -> UUID | None:
    return sesion.execute(
        text(
            "SELECT id FROM importacion WHERE complejo_id = :complejo AND huella = :huella "
            "AND estado <> 'descartada'"
        ),
        {"complejo": complejo_id, "huella": huella},
    ).scalar_one_or_none()


def _registrar_importacion(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    archivo: str,
    huella: str,
    fecha_de_migracion: date,
) -> UUID:
    """La importación queda en `borrador`; una subida nueva descarta el borrador anterior (E7)."""
    sesion.execute(
        text(
            "UPDATE importacion SET estado = 'descartada' "
            "WHERE complejo_id = :complejo AND estado = 'borrador'"
        ),
        {"complejo": complejo_id},
    )
    return UUID(
        str(
            sesion.execute(
                text(
                    "INSERT INTO importacion (administracion_id, complejo_id, archivo, huella, "
                    "fecha_de_migracion, creada_por) VALUES (:admin, :complejo, :archivo, :huella, "
                    ":fecha, :persona) RETURNING id"
                ),
                {
                    "admin": identidad.administracion_id,
                    "complejo": complejo_id,
                    "archivo": archivo,
                    "huella": huella,
                    "fecha": fecha_de_migracion,
                    "persona": identidad.persona_id,
                },
            ).scalar_one()
        )
    )


@dataclass(frozen=True)
class _PadronCargado:
    unidades: int
    propietarios_creados: int
    propietarios_reusados: int
    advertencias: tuple[ErrorDeImportacion, ...]


def _cargar_padron(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    padron: PadronValidado,
    request_id: UUID,
) -> _PadronCargado:
    """Cada unidad por `crear_unidad` (misma validación y auditoría que el alta manual; entra al
    grupo general con su coeficiente, que es el de la unidad) y su propietario **sin invitar**
    (E3)."""
    plan = agrupar_propietarios(padron.unidades)
    personas: dict[str, UUID] = {}
    creadas = reusadas = 0
    for unidad in padron.unidades:
        unidad_id = crear_unidad(
            sesion,
            identidad,
            complejo_id=complejo_id,
            datos={
                "identificador": unidad.identificador,
                "tipo": unidad.tipo,
                "piso": unidad.piso,
                "coeficiente": unidad.coeficiente.a_texto(),
                "superficie_m2": unidad.superficie_m2,
            },
            request_id=request_id,
        )
        if unidad.propietario is None:
            continue
        if unidad.email is not None and unidad.email in personas:
            persona_id = personas[unidad.email]
        else:
            nombre = plan.personas[unidad.email] if unidad.email else unidad.propietario
            persona = asegurar_persona(sesion, identidad, nombre=nombre, email=unidad.email)
            persona_id = persona.persona_id
            creadas += persona.creada
            reusadas += not persona.creada
            if unidad.email is not None:
                personas[unidad.email] = persona_id
        asignar_propietario(
            sesion, identidad, persona_id=persona_id, complejo_id=complejo_id, unidad_id=unidad_id
        )
    return _PadronCargado(
        len(padron.unidades), creadas, reusadas, (*padron.advertencias, *plan.advertencias)
    )


@accion_sensible(Accion.IMPORTAR_PADRON_Y_SALDOS)
def importar(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    contenido: bytes,
    nombre_del_archivo: str | None,
    fecha_de_migracion: date | None,
    lector: LectorDePlantilla,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> ResultadoDeImportacion:
    with transaccion(sesion, {}):
        _edificio_autorizado(sesion, identidad, complejo_id)
        # `None`: la ruta no pudo leerla (falta o mal escrita). Se rechaza recién acá para que el
        # 404 y el 403 (D7) ganen siempre.
        if fecha_de_migracion is None or fecha_de_migracion > hoy_en_mendoza(reloj):
            raise EntradaInvalida("fecha_de_migracion", "falta, es inválida o es posterior a hoy")
        # E8: el candado va antes de leer el estado, y el estado se lee ya con él puesto.
        edificio = cargar_complejo(sesion, complejo_id, bloquear=True)
        if edificio is None:
            raise NoEncontrado()
        if edificio.estado_migracion != "pendiente":
            raise Conflicto("estado_migracion")
        huella = hashlib.sha256(contenido).hexdigest()
        if (
            anterior := _importacion_vigente_con_la_huella(sesion, complejo_id, huella)
        ) is not None:
            raise ArchivoYaImportado(anterior)

        plantilla = lector.leer(contenido, nombre=nombre_del_archivo)
        existentes = listar_unidades(sesion, complejo_id)  # la única lectura del padrón (D1)
        vocabulario = (
            None
            if edificio.pisos is None or edificio.subsuelos is None
            else vocabulario_de_pisos(pisos=edificio.pisos, subsuelos=edificio.subsuelos)
        )
        padron = validar_padron(
            plantilla,
            ContextoDelEdificio(
                vocabulario_de_pisos=vocabulario, tiene_unidades=bool(existentes["unidades"])
            ),
        )

        importacion_id = _registrar_importacion(
            sesion,
            identidad,
            complejo_id=complejo_id,
            archivo=_nombre_del_archivo(nombre_del_archivo),
            huella=huella,
            fecha_de_migracion=fecha_de_migracion,
        )
        cargado = _cargar_padron(
            sesion, identidad, complejo_id=complejo_id, padron=padron, request_id=request_id
        )
        registrar(
            sesion,
            identidad,
            Accion.IMPORTAR_PADRON_Y_SALDOS,
            entidad="importacion",
            entidad_id=importacion_id,
            request_id=request_id,
            detalle={
                "complejo_id": str(complejo_id),
                "unidades": cargado.unidades,
                "propietarios_creados": cargado.propietarios_creados,
                "propietarios_reusados": cargado.propietarios_reusados,
            },
        )
    return ResultadoDeImportacion(
        importacion_id=importacion_id,
        unidades_creadas=cargado.unidades,
        propietarios_creados=cargado.propietarios_creados,
        propietarios_reusados=cargado.propietarios_reusados,
        filas_de_saldo=0,
        advertencias=cargado.advertencias,
    )
