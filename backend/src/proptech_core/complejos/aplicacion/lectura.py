"""Lectura mínima de `complejo`/`unidad` (D7, cambio 2a).

Nace acá, con lo mínimo que el candado necesita para cargar el recurso
dentro de la sesión ya filtrada por RLS (D5): `None` si no existe o es de
otra administración (RLS ya lo filtró). El resto del dominio de complejos
(crearlos, editarlos, D6) es del cambio 3; este módulo nunca importa
`acceso` (D-021, frontera verificada en `test_fronteras_de_modulos.py`).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.complejos.aplicacion.errores import NoEncontrado


@dataclass(frozen=True)
class ComplejoLeido:
    id: UUID
    administracion_id: UUID
    nombre: str
    localidad: str
    estado_migracion: str


@dataclass(frozen=True)
class UnidadLeida:
    id: UUID
    administracion_id: UUID
    complejo_id: UUID
    identificador: str
    tipo: str
    piso: str
    coeficiente: str
    superficie_m2: str


def cargar_complejo(sesion: Session, complejo_id: UUID) -> ComplejoLeido | None:
    fila = sesion.execute(
        text(
            "SELECT id, administracion_id, nombre, localidad, estado_migracion "
            "FROM complejo WHERE id = :id"
        ),
        {"id": str(complejo_id)},
    ).first()
    if fila is None:
        return None
    return ComplejoLeido(
        id=fila.id,
        administracion_id=fila.administracion_id,
        nombre=fila.nombre,
        localidad=fila.localidad,
        estado_migracion=fila.estado_migracion,
    )


def listar_complejos(sesion: Session) -> list[ComplejoLeido]:
    return [
        ComplejoLeido(**dict(fila))
        for fila in sesion.execute(
            text(
                "SELECT id, administracion_id, nombre, localidad, estado_migracion "
                "FROM complejo ORDER BY nombre, id"
            )
        ).mappings()
    ]


def cargar_unidad(sesion: Session, unidad_id: UUID) -> UnidadLeida | None:
    fila = sesion.execute(
        text(
            "SELECT id, administracion_id, complejo_id, identificador, tipo, piso, "
            "coeficiente::text, superficie_m2::text FROM unidad WHERE id = :id"
        ),
        {"id": str(unidad_id)},
    ).first()
    if fila is None:
        return None
    return UnidadLeida(
        id=fila.id,
        administracion_id=fila.administracion_id,
        complejo_id=fila.complejo_id,
        identificador=fila.identificador,
        tipo=fila.tipo,
        piso=fila.piso,
        coeficiente=fila.coeficiente,
        superficie_m2=fila.superficie_m2,
    )


def cargar_grupo(sesion: Session, grupo_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text("SELECT id, complejo_id FROM grupo_de_reparto WHERE id=:id"), {"id": grupo_id}
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


def cargar_categoria(sesion: Session, categoria_id: UUID) -> dict[str, Any] | None:
    fila = (
        sesion.execute(
            text("SELECT id, complejo_id FROM categoria_de_gasto WHERE id=:id"),
            {"id": categoria_id},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)


_COLUMNAS_CONFIGURACION = (
    "SELECT id, complejo_id, vigente_desde, tasa_mensual::text, dias_de_gracia, "
    "forma_de_calculo, porcentaje_fondo::text, dia_de_vencimiento, modalidad_de_vencimiento, "
    "dia_segundo_vencimiento, recargo_segundo_vencimiento::text, autor_id, creada_en "
    "FROM configuracion_versionada WHERE complejo_id=:id "
)


def listar_versiones(sesion: Session, complejo_id: UUID) -> list[dict[str, Any]]:
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    return [
        dict(f)
        for f in sesion.execute(
            text(_COLUMNAS_CONFIGURACION + "ORDER BY vigente_desde"), {"id": complejo_id}
        ).mappings()
    ]


def configuracion_vigente(sesion: Session, complejo_id: UUID, fecha: date) -> dict[str, Any] | None:
    if cargar_complejo(sesion, complejo_id) is None:
        raise NoEncontrado()
    fila = (
        sesion.execute(
            text(
                _COLUMNAS_CONFIGURACION
                + "AND vigente_desde<=:fecha ORDER BY vigente_desde DESC LIMIT 1"
            ),
            {"id": complejo_id, "fecha": fecha},
        )
        .mappings()
        .first()
    )
    return None if fila is None else dict(fila)
