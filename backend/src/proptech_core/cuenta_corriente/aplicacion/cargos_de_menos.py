"""Cargo cobrado de menos (liquidacion-y-emision, H-014, design E11; R08). Lo llama el 7, que
autoriza y audita.

Un cargo que se cobró de menos en una obligación ya emitida se corrige con una **obligación nueva**
sin emisión (con su `operacion_id`, como las del saldo inicial y el ajuste de la `0039`), en el
período de la obligación de origen, con vencimiento el día del registro (Mendoza) y el componente
que elige el administrador; más su fila en `cargo_cobrado_de_menos` con el motivo, el origen, quién
y cuándo. No toca ningún movimiento, obligación ni imputación existente (R08). El interés de R03 lo
calcula la emisión como a cualquier obligación: corre desde el día siguiente al vencimiento, nunca
uno retroactivo.

Todo se valida antes de escribir; lo escrito va en un SAVEPOINT. El replay se resuelve por
`operacion_id` (mismos datos: lo registrado, sin escribir; otros: conflicto) y se vuelve a mirar con
la cuenta bloqueada, para que dos pedidos simultáneos dejen un solo cargo.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.ajustes import COMPONENTES_DEL_AJUSTE
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    hoy,
    imputar_pendientes,
    normalizar_motivo,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import bloquear_cuentas, exigir_identidad
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    exigir_transaccion,
    traducir,
)

__all__ = ["COMPONENTES_DEL_CARGO", "CargoRegistrado", "registrar_cargo_cobrado_de_menos"]

#: Los tres componentes de capital; el interés no se carga (lo calcula la emisión).
COMPONENTES_DEL_CARGO = COMPONENTES_DEL_AJUSTE

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class CargoRegistrado:
    cargo_id: UUID
    operacion_id: UUID
    obligacion_id: UUID
    obligacion_origen_id: UUID
    cuenta_id: UUID
    unidad_id: UUID
    importe: Dinero
    componente: str
    periodo: date
    vencimiento: date
    motivo: str
    registrado_por: UUID
    registrado_en: datetime
    #: `True` si el `operacion_id` ya estaba registrado con los mismos datos (no se escribió nada).
    repetido: bool = False


def _validar(importe: Dinero, componente: str, motivo: str) -> str:
    """Devuelve el motivo normalizado (recortado, de 1 a 500)."""
    if componente not in COMPONENTES_DEL_CARGO:
        raise EntradaInvalida("componente")
    if importe <= _CERO:
        raise EntradaInvalida("importe")
    return normalizar_motivo(motivo)


def _componente_y_importe(ordinaria: str, fondo: str, extraordinaria: str) -> tuple[str, Dinero]:
    for nombre, valor in zip(
        COMPONENTES_DEL_CARGO, (ordinaria, fondo, extraordinaria), strict=True
    ):
        if Dinero(valor) > _CERO:
            return nombre, Dinero(valor)
    raise RuntimeError("el cargo registrado no tiene capital")  # lo impide el CHECK de importes


def _replay(
    sesion: Session,
    *,
    operacion_id: UUID,
    complejo_id: UUID,
    unidad_id: UUID,
    obligacion_origen_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
) -> CargoRegistrado | None:
    previo = sesion.execute(
        text(
            "SELECT a.id, a.obligacion_id, a.obligacion_origen_id, a.cuenta_id, a.complejo_id, "
            "c.unidad_id, o.periodo, o.vencimiento, o.ordinaria::text AS ordinaria, "
            "o.fondo_de_reserva::text AS fondo, o.extraordinaria::text AS extraordinaria, "
            "a.motivo, a.registrado_por, a.registrado_en FROM cargo_cobrado_de_menos a "
            "JOIN obligacion o ON o.id = a.obligacion_id JOIN cuenta c ON c.id = a.cuenta_id "
            "WHERE a.operacion_id = :op"
        ),
        {"op": operacion_id},
    ).one_or_none()
    if previo is None:
        return None
    registrado, monto = _componente_y_importe(previo.ordinaria, previo.fondo, previo.extraordinaria)
    mismos = (
        previo.complejo_id == complejo_id
        and previo.unidad_id == unidad_id
        and previo.obligacion_origen_id == obligacion_origen_id
        and registrado == componente
        and monto == importe
        and previo.motivo == motivo
    )
    if not mismos:
        raise Conflicto("operacion_id")
    return CargoRegistrado(
        cargo_id=UUID(str(previo.id)),
        operacion_id=operacion_id,
        obligacion_id=UUID(str(previo.obligacion_id)),
        obligacion_origen_id=obligacion_origen_id,
        cuenta_id=UUID(str(previo.cuenta_id)),
        unidad_id=unidad_id,
        importe=monto,
        componente=registrado,
        periodo=previo.periodo,
        vencimiento=previo.vencimiento,
        motivo=previo.motivo,
        registrado_por=UUID(str(previo.registrado_por)),
        registrado_en=previo.registrado_en,
        repetido=True,
    )


def registrar_cargo_cobrado_de_menos(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    obligacion_origen_id: UUID,
    operacion_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> CargoRegistrado:
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    instante = reloj()
    vencimiento = hoy(lambda: instante)  # el día del registro, en Mendoza (la regla de `hoy`)
    limpio = _validar(importe, componente, motivo)

    def anterior() -> CargoRegistrado | None:
        return _replay(
            sesion,
            operacion_id=operacion_id,
            complejo_id=complejo_id,
            unidad_id=unidad_id,
            obligacion_origen_id=obligacion_origen_id,
            importe=importe,
            componente=componente,
            motivo=limpio,
        )

    previo = anterior()  # sin escribir: un conflicto no deja nada
    if previo is not None:
        return previo
    # El origen es una obligación de esta unidad y de este edificio (si no, 404 sin distinguir).
    origen = sesion.execute(
        text(
            "SELECT o.cuenta_id, o.periodo FROM obligacion o JOIN cuenta c ON c.id = o.cuenta_id "
            "WHERE o.id = :o AND o.complejo_id = :c AND c.unidad_id = :u"
        ),
        {"o": obligacion_origen_id, "c": complejo_id, "u": unidad_id},
    ).one_or_none()
    if origen is None:
        raise NoEncontrado
    cuenta = UUID(str(origen.cuenta_id))
    periodo: date = origen.periodo
    columnas = {c: (importe if c == componente else _CERO) for c in COMPONENTES_DEL_CARGO}
    with sesion.begin_nested():
        bloquear_cuentas(sesion, [cuenta])
        previo = anterior()  # otra transacción pudo ganar mientras esperábamos
        if previo is not None:
            return previo
        obligacion, cargo = uuid4(), uuid4()
        with traducir(sesion, {}):
            sesion.execute(
                text(
                    "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, "
                    "operacion_id, periodo, vencimiento, ordinaria, fondo_de_reserva, "
                    "extraordinaria, registrada_en) VALUES (:id, :adm, :c, :cuenta, :op, :p, :v, "
                    ":o, :f, :x, :en)"
                ),
                {
                    "id": obligacion,
                    "adm": administracion,
                    "c": complejo_id,
                    "cuenta": cuenta,
                    "op": operacion_id,
                    "p": periodo,
                    "v": vencimiento,
                    "o": columnas["ordinaria"].a_texto(),
                    "f": columnas["fondo_de_reserva"].a_texto(),
                    "x": columnas["extraordinaria"].a_texto(),
                    "en": instante,
                },
            )
            sesion.execute(
                text(
                    "INSERT INTO cargo_cobrado_de_menos (id, administracion_id, complejo_id, "
                    "cuenta_id, obligacion_id, obligacion_origen_id, operacion_id, motivo, "
                    "registrado_por, request_id, registrado_en) VALUES (:id, :adm, :c, :cuenta, "
                    ":obl, :origen, :op, :motivo, :por, :req, :en)"
                ),
                {
                    "id": cargo,
                    "adm": administracion,
                    "c": complejo_id,
                    "cuenta": cuenta,
                    "obl": obligacion,
                    "origen": obligacion_origen_id,
                    "op": operacion_id,
                    "motivo": limpio,
                    "por": identidad.persona_id,
                    "req": request_id,
                    "en": instante,
                },
            )
        imputar_pendientes(sesion, cuenta, uuid4(), instante)  # un crédito a favor, R04
    return CargoRegistrado(
        cargo_id=cargo,
        operacion_id=operacion_id,
        obligacion_id=obligacion,
        obligacion_origen_id=obligacion_origen_id,
        cuenta_id=cuenta,
        unidad_id=unidad_id,
        importe=importe,
        componente=componente,
        periodo=periodo,
        vencimiento=vencimiento,
        motivo=limpio,
        registrado_por=identidad.persona_id,
        registrado_en=instante,
    )
