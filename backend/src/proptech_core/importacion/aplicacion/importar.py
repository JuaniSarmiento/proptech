"""PROVISORIO (rojo de la tarea 1.5): no escribe nada."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.importacion.dominio.plantilla import ErrorDeImportacion
from proptech_core.importacion.puertos import LectorDePlantilla


@dataclass(frozen=True)
class ResultadoDeImportacion:
    importacion_id: UUID
    unidades_creadas: int
    propietarios_creados: int
    propietarios_reusados: int
    filas_de_saldo: int
    advertencias: tuple[ErrorDeImportacion, ...]


def importar(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    contenido: bytes,
    nombre_del_archivo: str | None,
    fecha_de_migracion: date,
    lector: LectorDePlantilla,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> ResultadoDeImportacion:
    return ResultadoDeImportacion(uuid4(), 0, 0, 0, 0, ())
