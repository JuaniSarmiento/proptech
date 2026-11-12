"""El borrador de saldos de una importación (design D5, D6): guardarlo sin tocar el libro, leer el
vigente y compararlo con el control, y leer su aceptación.

Las tablas son `fila_de_saldo_importada`, `control_de_saldo` y `aceptacion_de_diferencias` (`0037`),
todas de este módulo. Los nombres de las unidades se piden a `complejos.aplicacion`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.unidades import listar_unidades
from proptech_core.importacion.dominio.comparacion import (
    Comparacion,
    SaldoGuardado,
    comparar_saldos,
)
from proptech_core.importacion.dominio.saldos import BorradorValidado


@dataclass(frozen=True)
class BorradorVigente:
    importacion_id: UUID
    fecha_de_migracion: date


@dataclass(frozen=True)
class DiferenciaAceptada:
    """Una unidad cuya diferencia se aceptó; los montos como texto con dos decimales."""

    unidad: str
    borrador: str
    control: str
    diferencia: str


@dataclass(frozen=True)
class AceptacionRegistrada:
    aceptacion_id: UUID
    diferencias: tuple[DiferenciaAceptada, ...]
    aceptada_por: UUID
    aceptada_en: datetime


def guardar_borrador(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    importacion_id: UUID,
    borrador: BorradorValidado,
    unidades: Mapping[str, UUID],
) -> None:
    """Guarda las filas de `Saldos` y de `Control` ya validadas. `unidades` traduce cada
    identificador a su id. No toca cuentas, obligaciones ni movimientos."""
    comunes = {
        "administracion": identidad.administracion_id,
        "complejo": complejo_id,
        "importacion": importacion_id,
    }
    if borrador.filas:
        sesion.execute(
            text(
                "INSERT INTO fila_de_saldo_importada (administracion_id, complejo_id, "
                "importacion_id, unidad_id, fila, tipo, periodo, vencimiento, concepto, importe, "
                "interes_acumulado) VALUES (:administracion, :complejo, :importacion, :unidad, "
                ":fila, :tipo, :periodo, :vencimiento, :concepto, CAST(:importe AS NUMERIC), "
                "CAST(:interes AS NUMERIC))"
            ),
            [
                {
                    **comunes,
                    "unidad": unidades[f.unidad],
                    "fila": f.fila,
                    "tipo": f.tipo,
                    "periodo": f.periodo,
                    "vencimiento": f.vencimiento,
                    "concepto": f.concepto,
                    "importe": f.importe.a_texto(),
                    "interes": f.interes_acumulado.a_texto(),
                }
                for f in borrador.filas
            ],
        )
    if borrador.controles:
        sesion.execute(
            text(
                "INSERT INTO control_de_saldo (administracion_id, complejo_id, importacion_id, "
                "unidad_id, fila, saldo) VALUES (:administracion, :complejo, :importacion, "
                ":unidad, :fila, CAST(:saldo AS NUMERIC))"
            ),
            [
                {
                    **comunes,
                    "unidad": unidades[c.unidad],
                    "fila": c.fila,
                    "saldo": c.saldo.a_texto(),
                }
                for c in borrador.controles
            ],
        )


def borrador_vigente(sesion: Session, complejo_id: UUID) -> BorradorVigente | None:
    """El único borrador del edificio (el de la última subida), o `None`."""
    fila = sesion.execute(
        text(
            "SELECT id, fecha_de_migracion FROM importacion "
            "WHERE complejo_id = :complejo AND estado = 'borrador'"
        ),
        {"complejo": complejo_id},
    ).one_or_none()
    return None if fila is None else BorradorVigente(UUID(str(fila[0])), fila[1])


def comparar_importacion(sesion: Session, complejo_id: UUID, importacion_id: UUID) -> Comparacion:
    """El borrador de esa importación contra su control, unidad por unidad (sin el aviso, que
    depende de la configuración)."""
    nombres = {
        UUID(str(u["id"])): str(u["identificador"])
        for u in listar_unidades(sesion, complejo_id)["unidades"]
    }
    filas = [
        SaldoGuardado(UUID(str(f[0])), str(f[1]), Dinero(str(f[2])), Dinero(str(f[3])))
        for f in sesion.execute(
            text(
                "SELECT unidad_id, tipo, importe::text, interes_acumulado::text "
                "FROM fila_de_saldo_importada WHERE importacion_id = :importacion"
            ),
            {"importacion": importacion_id},
        )
    ]
    controles = {
        UUID(str(c[0])): Dinero(str(c[1]))
        for c in sesion.execute(
            text(
                "SELECT unidad_id, saldo::text FROM control_de_saldo "
                "WHERE importacion_id = :importacion"
            ),
            {"importacion": importacion_id},
        )
    }
    return comparar_saldos(nombres, filas, controles)


def leer_aceptacion(sesion: Session, importacion_id: UUID) -> AceptacionRegistrada | None:
    """La aceptación de **esa** importación (la de un borrador descartado no vale para otro)."""
    fila = sesion.execute(
        text(
            "SELECT id, diferencias, aceptada_por, aceptada_en FROM aceptacion_de_diferencias "
            "WHERE importacion_id = :importacion"
        ),
        {"importacion": importacion_id},
    ).one_or_none()
    if fila is None:
        return None
    return AceptacionRegistrada(
        aceptacion_id=UUID(str(fila[0])),
        diferencias=tuple(
            DiferenciaAceptada(d["unidad"], d["borrador"], d["control"], d["diferencia"])
            for d in fila[1]
        ),
        aceptada_por=UUID(str(fila[2])),
        aceptada_en=fila[3],
    )
