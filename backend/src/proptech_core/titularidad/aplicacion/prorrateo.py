"""El prorrateo por días de la expensa del mes del cambio, en el libro (H-032, R32, D-168.5).

Un cambio con `expensa_del_mes = "prorrateo"` deja una fila en `prorrateo_de_cambio` (única por
unidad y período). Si el período del mes ya está emitido, se aplica en el acto, en la transacción
del cambio; si no, queda pendiente y lo aplica `aplicar_prorrateos_pendientes` en la transacción
de la emisión de ese período (la llama `liquidacion`, que ya tiene el candado del edificio). Aplicar es
trasladar a la cuenta del vendedor deudor, por componente, `max(parte por días - ya pagado, 0)`
(`dominio/prorrateo.py`) con las piezas del traslado de H-031, y dejar una fila en
`prorrateo_aplicado` con lo trasladado: la tabla no admite `UPDATE`, así que pendiente es no tener
esa fila. Nunca toca el interés. No commitea: lo hace el llamador.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.liquidar import periodos_emitidos
from proptech_core.cuenta_corriente.aplicacion.traslado_de_deuda import trasladar_parte_del_mes
from proptech_core.titularidad.dominio.prorrateo import (
    dias_del_mes,
    dias_del_vendedor,
    parte_a_trasladar,
)

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class _Pendiente:
    prorrateo_id: UUID
    cambio_id: UUID
    unidad_id: UUID
    complejo_id: UUID
    fecha: date
    deudor_id: UUID
    dias_del_vendedor: int
    dias_del_mes: int


def prorrateo_ya_pedido(sesion: Session, *, unidad_id: UUID, fecha: date) -> bool:
    """N02: la unidad ya tiene un prorrateo (pendiente o aplicado) en el mes de `fecha`."""
    return (
        sesion.execute(
            text(
                "SELECT 1 FROM prorrateo_de_cambio WHERE unidad_id = :unidad AND periodo = :periodo"
            ),
            {"unidad": unidad_id, "periodo": fecha.replace(day=1)},
        ).first()
        is not None
    )


def pedir_prorrateo(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    cambio_id: UUID,
    unidad_id: UUID,
    fecha: date,
    deudor_id: UUID,
    request_id: UUID,
) -> Dinero | None:
    """Guarda el prorrateo del cambio y, si el período ya está emitido, lo aplica. Devuelve lo
    trasladado, o `None` si quedó pendiente."""
    prorrateo_id = uuid4()
    dias, del_mes = dias_del_vendedor(fecha), dias_del_mes(fecha)
    sesion.execute(
        text(
            "INSERT INTO prorrateo_de_cambio (id, administracion_id, complejo_id, cambio_id, "
            "unidad_id, periodo, dias_del_vendedor, dias_del_mes) VALUES (:id, :administracion, "
            ":complejo, :cambio, :unidad, :periodo, :dias, :del_mes)"
        ),
        {
            "id": prorrateo_id,
            "administracion": identidad.administracion_id,
            "complejo": complejo_id,
            "cambio": cambio_id,
            "unidad": unidad_id,
            "periodo": fecha.replace(day=1),
            "dias": dias,
            "del_mes": del_mes,
        },
    )
    if fecha.replace(day=1) not in periodos_emitidos(sesion, complejo_id=complejo_id):
        return None
    return _aplicar(
        sesion,
        identidad,
        _Pendiente(
            prorrateo_id, cambio_id, unidad_id, complejo_id, fecha, deudor_id, dias, del_mes
        ),
        request_id,
    )


def aplicar_prorrateos_pendientes(
    sesion: Session, identidad: Identidad, *, complejo_id: UUID, periodo: date, request_id: UUID
) -> list[UUID]:
    """Aplica los prorrateos pendientes del período, del cambio más viejo al más nuevo. La emisión
    ya tiene el candado del edificio: un cambio que se registra en el medio espera o ve el período
    emitido. Idempotente: lo aplicado deja de ser pendiente. Devuelve los cambios aplicados."""
    filas = sesion.execute(
        text(
            "SELECT p.id, p.cambio_id, p.unidad_id, c.fecha, c.vendedor_deudor_id, "
            "p.dias_del_vendedor, p.dias_del_mes FROM prorrateo_de_cambio p "
            "JOIN cambio_de_titular c ON c.administracion_id = p.administracion_id "
            "AND c.complejo_id = p.complejo_id AND c.id = p.cambio_id "
            "WHERE p.complejo_id = :complejo AND p.periodo = :periodo AND NOT EXISTS "
            "(SELECT 1 FROM prorrateo_aplicado a WHERE a.administracion_id = p.administracion_id "
            "AND a.prorrateo_id = p.id) ORDER BY c.registrado_en, c.id"
        ),
        {"complejo": complejo_id, "periodo": periodo.replace(day=1)},
    ).all()
    aplicados: list[UUID] = []
    for f in filas:
        _aplicar(
            sesion,
            identidad,
            _Pendiente(
                f.id,
                f.cambio_id,
                f.unidad_id,
                complejo_id,
                f.fecha,
                f.vendedor_deudor_id,
                f.dias_del_vendedor,
                f.dias_del_mes,
            ),
            request_id,
        )
        aplicados.append(f.cambio_id)
    return aplicados


def _aplicar(
    sesion: Session, identidad: Identidad, pendiente: _Pendiente, request_id: UUID
) -> Dinero:
    traslado = trasladar_parte_del_mes(
        sesion,
        identidad,
        cambio_id=pendiente.cambio_id,
        unidad_id=pendiente.unidad_id,
        persona_id=pendiente.deudor_id,
        fecha=pendiente.fecha,
        regla=lambda emitido, impago: parte_a_trasladar(
            emitido, impago, pendiente.dias_del_vendedor, pendiente.dias_del_mes
        ),
        request_id=request_id,
    )
    sesion.execute(
        text(
            "INSERT INTO prorrateo_aplicado (administracion_id, complejo_id, prorrateo_id, "
            "parte_del_vendedor) VALUES (:administracion, :complejo, :prorrateo, :parte)"
        ),
        {
            "administracion": identidad.administracion_id,
            "complejo": pendiente.complejo_id,
            "prorrateo": pendiente.prorrateo_id,
            "parte": traslado.trasladado.decimal,
        },
    )
    return traslado.trasladado


def hay_prorrateo_aplicado(sesion: Session, *, complejo_id: UUID, periodo: date) -> bool:
    """N01: el período tiene un prorrateo que movió plata al libro (más de cero). Anular su emisión
    no tiene todavía cómo deshacerlo (deuda anotada en la ficha del 4d)."""
    return (
        sesion.execute(
            text(
                "SELECT 1 FROM prorrateo_de_cambio p JOIN prorrateo_aplicado a "
                "ON a.administracion_id = p.administracion_id AND a.prorrateo_id = p.id "
                "WHERE p.complejo_id = :complejo AND p.periodo = :periodo "
                "AND a.parte_del_vendedor > 0 LIMIT 1"
            ),
            {"complejo": complejo_id, "periodo": periodo.replace(day=1)},
        ).first()
        is not None
    )
