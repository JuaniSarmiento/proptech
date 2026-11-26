"""Los cambios de titular de una unidad, el más nuevo primero (H-030, C06)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.titularidad.aplicacion.autorizacion import unidad_autorizada


@dataclass(frozen=True)
class CompradorDelCambio:
    persona_id: UUID
    nombre: str
    email: str | None


@dataclass(frozen=True)
class CambioDeTitular:
    id: UUID
    unidad_id: UUID
    fecha: date
    vendedores: tuple[UUID, ...]
    compradores: tuple[CompradorDelCambio, ...]
    expensa_del_mes: str
    deuda_previa: str
    registrado_por: UUID
    registrado_en: datetime
    #: Sólo en la respuesta del registro: la deuda de la unidad en ese momento, si había.
    aviso: Dinero | None = None
    #: Sólo en la respuesta de un registro con la deuda a nombre del vendedor (H-031): lo trasladado
    #: y la cuenta de persona que lo recibió (`None` si no había deuda previa que trasladar).
    trasladado: Dinero | None = None
    cuenta_del_vendedor: UUID | None = None


def listar_cambios(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, unidad_id: UUID
) -> list[CambioDeTitular]:
    unidad_autorizada(sesion, identidad, complejo_id, unidad_id)
    cambios = sesion.execute(
        text(
            "SELECT id, unidad_id, fecha, expensa_del_mes, deuda_previa, registrado_por, "
            "registrado_en FROM cambio_de_titular WHERE unidad_id = :unidad "
            "ORDER BY fecha DESC, registrado_en DESC, id DESC"
        ),
        {"unidad": unidad_id},
    ).all()
    personas = sesion.execute(
        text(
            "SELECT p.cambio_id, p.persona_id, p.rol, p.nombre, p.email "
            "FROM parte_de_cambio_de_titular p "
            "JOIN cambio_de_titular c ON c.id = p.cambio_id "
            "AND c.administracion_id = p.administracion_id "
            "WHERE c.unidad_id = :unidad ORDER BY p.cambio_id, p.rol, p.orden"
        ),
        {"unidad": unidad_id},
    ).all()
    vendedores: dict[UUID, list[UUID]] = {}
    compradores: dict[UUID, list[CompradorDelCambio]] = {}
    for fila in personas:
        if fila.rol == "vendedor":
            vendedores.setdefault(fila.cambio_id, []).append(fila.persona_id)
        else:
            compradores.setdefault(fila.cambio_id, []).append(
                CompradorDelCambio(fila.persona_id, fila.nombre, fila.email)
            )
    return [
        CambioDeTitular(
            id=c.id,
            unidad_id=c.unidad_id,
            fecha=c.fecha,
            vendedores=tuple(vendedores.get(c.id, [])),
            compradores=tuple(compradores.get(c.id, [])),
            expensa_del_mes=c.expensa_del_mes,
            deuda_previa=c.deuda_previa,
            registrado_por=c.registrado_por,
            registrado_en=c.registrado_en,
        )
        for c in cambios
    ]
