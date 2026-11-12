"""Ajuste de saldo inicial (importacion-desde-excel, H-010, design D8, E11; D-155). Lo llama el 5,
que autoriza y audita.

El ajuste corrige un saldo inicial cargado de menos con una **obligación nueva** sin emisión (con su
`operacion_id`, como las del saldo inicial) más su fila en `ajuste_de_saldo_inicial` con el motivo.
No toca ningún movimiento ni obligación existente (R08) y no necesita una obligación previa: sirve
igual para una unidad sin cuenta o con crédito a favor (se imputa, R04). El interés de R03 lo
calcula la emisión como a cualquier obligación: corre desde el día siguiente al vencimiento, que es
el día del ajuste (nunca uno retroactivo).

Todo se valida antes de escribir; lo escrito va en un SAVEPOINT. El replay se resuelve por
`operacion_id` (mismos datos: lo registrado, sin escribir; otros: conflicto) y se vuelve a mirar con
la cuenta bloqueada, para que dos pedidos simultáneos dejen un solo ajuste.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    hoy,
    imputar_pendientes,
    normalizar_motivo,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import (
    bloquear_cuentas,
    cuenta_de_unidad,
    exigir_identidad,
)
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    exigir_transaccion,
    traducir,
)

__all__ = ["COMPONENTES_DEL_AJUSTE", "AjusteRegistrado", "registrar_ajuste_de_saldo_inicial"]

#: Los tres componentes de capital; el interés no se ajusta (lo calcula la emisión).
COMPONENTES_DEL_AJUSTE = ("ordinaria", "fondo_de_reserva", "extraordinaria")

_CERO = Dinero("0.00")


@dataclass(frozen=True)
class AjusteRegistrado:
    ajuste_id: UUID
    operacion_id: UUID
    obligacion_id: UUID
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
    if componente not in COMPONENTES_DEL_AJUSTE:
        raise EntradaInvalida("componente")
    if importe <= _CERO:
        raise EntradaInvalida("importe")
    return normalizar_motivo(motivo)


def _componente_y_importe(ordinaria: str, fondo: str, extraordinaria: str) -> tuple[str, Dinero]:
    for nombre, valor in zip(
        COMPONENTES_DEL_AJUSTE, (ordinaria, fondo, extraordinaria), strict=True
    ):
        if Dinero(valor) > _CERO:
            return nombre, Dinero(valor)
    raise RuntimeError("el ajuste registrado no tiene capital")  # lo impide el CHECK de importes


def _replay(
    sesion: Session,
    *,
    operacion_id: UUID,
    complejo_id: UUID,
    unidad_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
) -> AjusteRegistrado | None:
    previo = sesion.execute(
        text(
            "SELECT a.id, a.obligacion_id, a.cuenta_id, a.complejo_id, c.unidad_id, o.periodo, "
            "o.vencimiento, o.ordinaria::text AS ordinaria, o.fondo_de_reserva::text AS fondo, "
            "o.extraordinaria::text AS extraordinaria, a.motivo, a.registrado_por, a.registrado_en "
            "FROM ajuste_de_saldo_inicial a JOIN obligacion o ON o.id = a.obligacion_id "
            "JOIN cuenta c ON c.id = a.cuenta_id WHERE a.operacion_id = :op"
        ),
        {"op": operacion_id},
    ).one_or_none()
    if previo is None:
        return None
    registrado, monto = _componente_y_importe(previo.ordinaria, previo.fondo, previo.extraordinaria)
    mismos = (
        previo.complejo_id == complejo_id
        and previo.unidad_id == unidad_id
        and registrado == componente
        and monto == importe
        and previo.motivo == motivo
    )
    if not mismos:
        raise Conflicto("operacion_id")
    return AjusteRegistrado(
        ajuste_id=UUID(str(previo.id)),
        operacion_id=operacion_id,
        obligacion_id=UUID(str(previo.obligacion_id)),
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


def _fecha_de_migracion(sesion: Session, complejo_id: UUID) -> date:
    """La de la carga de saldo inicial del edificio; sin carga no hay migración que ajustar."""
    fecha = sesion.execute(
        text("SELECT fecha_de_migracion FROM carga_de_saldo_inicial WHERE complejo_id = :c"),
        {"c": complejo_id},
    ).scalar_one_or_none()
    if fecha is None:
        raise Conflicto("estado_migracion")
    return fecha  # type: ignore[no-any-return]


def registrar_ajuste_de_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    operacion_id: UUID,
    importe: Dinero,
    componente: str,
    motivo: str,
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> AjusteRegistrado:
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    instante = reloj()
    vencimiento = hoy(lambda: instante)  # el día del ajuste, en Mendoza (la regla de `hoy`)
    limpio = _validar(importe, componente, motivo)

    def anterior() -> AjusteRegistrado | None:
        return _replay(
            sesion,
            operacion_id=operacion_id,
            complejo_id=complejo_id,
            unidad_id=unidad_id,
            importe=importe,
            componente=componente,
            motivo=limpio,
        )

    previo = anterior()  # sin crear nada: un conflicto no deja ni una cuenta
    if previo is not None:
        return previo
    fecha = _fecha_de_migracion(sesion, complejo_id)
    periodo = date(fecha.year, fecha.month, 1)
    columnas = {c: (importe if c == componente else _CERO) for c in COMPONENTES_DEL_AJUSTE}
    with sesion.begin_nested():
        cuenta = cuenta_de_unidad(sesion, complejo_id=complejo_id, unidad_id=unidad_id)
        bloquear_cuentas(sesion, [cuenta])
        previo = anterior()  # otra transacción pudo ganar mientras esperábamos
        if previo is not None:
            return previo
        obligacion, ajuste = uuid4(), uuid4()
        with traducir(sesion, {"uq_ajuste_operacion": "operacion_id"}):
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
                    "INSERT INTO ajuste_de_saldo_inicial (id, administracion_id, complejo_id, "
                    "cuenta_id, obligacion_id, operacion_id, motivo, registrado_por, request_id, "
                    "registrado_en) VALUES (:id, :adm, :c, :cuenta, :obl, :op, :motivo, :por, "
                    ":req, :en)"
                ),
                {
                    "id": ajuste,
                    "adm": administracion,
                    "c": complejo_id,
                    "cuenta": cuenta,
                    "obl": obligacion,
                    "op": operacion_id,
                    "motivo": limpio,
                    "por": identidad.persona_id,
                    "req": request_id,
                    "en": instante,
                },
            )
        imputar_pendientes(sesion, cuenta, uuid4(), instante)  # un crédito a favor, R04
    return AjusteRegistrado(
        ajuste_id=ajuste,
        operacion_id=operacion_id,
        obligacion_id=obligacion,
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
