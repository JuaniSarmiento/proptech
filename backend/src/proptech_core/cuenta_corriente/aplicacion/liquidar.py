"""Lecturas del libro para liquidar (7, E4, R40): el interés a cobrar y los períodos emitidos.

Son lecturas: sin candados ni escrituras. La preliquidación las pide antes de que nadie emita, y
la emisión recalcula bajo candado (E3 detecta cualquier diferencia con la huella).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.aplicacion.cobranza import SENTENCIA_DE_COBRANZA
from proptech_core.cuenta_corriente.aplicacion.emisiones import calcular_intereses_del_corte
from proptech_core.cuenta_corriente.aplicacion.lecturas import fotos_del_edificio


def intereses_a_cobrar(sesion: Session, *, complejo_id: UUID, periodo: date) -> dict[UUID, Dinero]:
    """Lo que `registrar_emision` registraría hoy de interés para el período, por unidad: la
    misma función (`calcular_intereses`), las mismas fotos de las cuentas de unidad del edificio y
    la misma versión de configuración, con el corte en el último día del mes anterior (E2 del 4c).
    Una unidad sin cuenta, o sin interés, no figura."""
    corte = periodo - timedelta(days=1)
    actuales = {
        f.cuenta_id: f
        for f in fotos_del_edificio(sesion, complejo_id, SENTENCIA_DE_COBRANZA)
        if f.unidad_id is not None
    }
    _, calculados = calcular_intereses_del_corte(sesion, complejo_id, corte, actuales)
    resultado: dict[UUID, Dinero] = {}
    for cuenta, intereses in calculados.items():
        unidad = actuales[cuenta].unidad_id
        if unidad is not None and intereses:
            resultado[unidad] = sumar(i.importe for i in intereses)
    return resultado


def periodos_emitidos(sesion: Session, *, complejo_id: UUID) -> Sequence[date]:
    """Los períodos del edificio con una emisión sin anular (R40): una fila en `emision` sin
    evento `anulada`. Una emisión anulada no cuenta."""
    filas = sesion.execute(
        text(
            "SELECT DISTINCT e.periodo FROM emision e WHERE e.complejo_id = :c AND NOT EXISTS "
            "(SELECT 1 FROM evento_de_emision v WHERE v.administracion_id = e.administracion_id "
            "AND v.emision_id = e.id AND v.tipo = 'anulada') ORDER BY e.periodo"
        ),
        {"c": complejo_id},
    ).scalars()
    return [p if isinstance(p, date) else date.fromisoformat(str(p)) for p in filas]


def hay_emision_posterior(sesion: Session, *, complejo_id: UUID, periodo: date) -> bool:
    """P26: el edificio tiene una emisión sin anular de un período posterior a `periodo`."""
    return any(p > periodo for p in periodos_emitidos(sesion, complejo_id=complejo_id))


@dataclass(frozen=True)
class CierreDeEmision:
    """Cómo se cerró una emisión (E9, E10): distribuida (con su origen) o anulada (motivo)."""

    tipo: str
    origen: str | None
    motivo: str | None
    persona_id: UUID | None
    en: datetime


def cierres_de_emisiones(
    sesion: Session, emision_ids: Sequence[UUID]
) -> dict[UUID, CierreDeEmision]:
    """El evento de cierre de cada emisión que lo tenga; una emisión sin evento sigue emitida. A lo
    sumo uno por emisión (el índice parcial único de la `0042`)."""
    if not emision_ids:
        return {}
    filas = sesion.execute(
        text(
            "SELECT emision_id, tipo, origen, motivo, persona_id, registrado_en "
            "FROM evento_de_emision WHERE emision_id = ANY(:ids) "
            "AND tipo IN ('anulada', 'distribuida')"
        ).bindparams(bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))),
        {"ids": list(emision_ids)},
    )
    return {
        UUID(str(f.emision_id)): CierreDeEmision(
            f.tipo,
            f.origen,
            f.motivo,
            None if f.persona_id is None else UUID(str(f.persona_id)),
            f.registrado_en,
        )
        for f in filas
    }
