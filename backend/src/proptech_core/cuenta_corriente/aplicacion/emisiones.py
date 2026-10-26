"""Emisión y anulación (D4, E3, R17). Lo llama el 7, que autoriza y audita."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion.creditos import (
    Reloj,
    ahora_utc,
    imputar_pendientes,
    normalizar_motivo,
)
from proptech_core.cuenta_corriente.aplicacion.cuentas import (
    bloquear_cuentas,
    crear_cuentas_de_unidades,
    exigir_identidad,
)
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
    exigir_transaccion,
    traducir,
)
from proptech_core.cuenta_corriente.aplicacion.lecturas import foto

_CERO = Dinero("0.00")
_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))


@dataclass(frozen=True)
class ObligacionAEmitir:
    unidad_id: UUID
    vencimiento: date
    ordinaria: Dinero
    fondo_de_reserva: Dinero
    extraordinaria: Dinero


@dataclass(frozen=True)
class EmisionRegistrada:
    emision_id: UUID
    intento: int
    cuentas: dict[UUID, UUID]  # unidad -> cuenta
    #: D12, R06: la foto que el 7 publica, tomada bajo el candado después de imputar pendientes.
    saldo_anterior: dict[UUID, Dinero]  # cuenta -> saldo anterior


def _validar(periodo: date, obligaciones: Sequence[ObligacionAEmitir]) -> None:
    if periodo.day != 1:
        raise EntradaInvalida("periodo")
    if not obligaciones:
        raise EntradaInvalida("obligaciones")
    if len({o.unidad_id for o in obligaciones}) != len(obligaciones):
        raise EntradaInvalida("obligaciones")
    for o in obligaciones:
        partes = (o.ordinaria, o.fondo_de_reserva, o.extraordinaria)
        if any(p < _CERO for p in partes) or not (
            o.ordinaria + o.fondo_de_reserva + o.extraordinaria > _CERO
        ):
            raise EntradaInvalida("obligaciones")


def _firma(obligaciones: Sequence[ObligacionAEmitir]) -> list[tuple[str, ...]]:
    return sorted(
        (
            str(o.unidad_id),
            o.vencimiento.isoformat(),
            o.ordinaria.a_texto(),
            o.fondo_de_reserva.a_texto(),
            o.extraordinaria.a_texto(),
        )
        for o in obligaciones
    )


def _replay(
    sesion: Session,
    emision_id: UUID,
    complejo_id: UUID,
    periodo: date,
    obligaciones: Sequence[ObligacionAEmitir],
) -> EmisionRegistrada | None:
    fila = sesion.execute(
        text("SELECT complejo_id, periodo, intento FROM emision WHERE id = :id"), {"id": emision_id}
    ).one_or_none()
    if fila is None:
        return None
    guardadas = sesion.execute(
        text(
            "SELECT c.unidad_id, c.id AS cuenta_id, o.vencimiento, o.ordinaria::text AS ordinaria, "
            "o.fondo_de_reserva::text AS fondo, o.extraordinaria::text AS extra "
            "FROM obligacion o JOIN cuenta c ON c.id = o.cuenta_id "
            "AND c.administracion_id = o.administracion_id WHERE o.emision_id = :id"
        ),
        {"id": emision_id},
    ).all()
    firma = sorted(
        (str(g.unidad_id), g.vencimiento.isoformat(), g.ordinaria, g.fondo, g.extra)
        for g in guardadas
    )
    if (fila.complejo_id, fila.periodo) != (complejo_id, periodo) or firma != _firma(obligaciones):
        raise Conflicto("emision_id")
    cuentas = {UUID(str(g.unidad_id)): UUID(str(g.cuenta_id)) for g in guardadas}
    return EmisionRegistrada(emision_id, fila.intento, cuentas, {})


def registrar_emision(
    sesion: Session,
    identidad: Identidad,
    *,
    emision_id: UUID,
    complejo_id: UUID,
    periodo: date,
    obligaciones: Sequence[ObligacionAEmitir],
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> EmisionRegistrada:
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    _validar(periodo, obligaciones)
    # Paso 1: replay por id.
    previo = _replay(sesion, emision_id, complejo_id, periodo, obligaciones)
    if previo is not None:
        return previo
    if (
        sesion.execute(
            text("SELECT 1 FROM complejo WHERE id = :c"), {"c": complejo_id}
        ).one_or_none()
        is None
    ):
        raise NoEncontrado
    # Paso 2: intentos y anulaciones del período, antes de insertar.
    intentos = sesion.execute(
        text(
            "SELECT e.intento, EXISTS (SELECT 1 FROM evento_de_emision v WHERE v.emision_id = e.id "
            "AND v.tipo = 'anulada') AS anulada FROM emision e "
            "WHERE e.complejo_id = :c AND e.periodo = :p"
        ),
        {"c": complejo_id, "p": periodo},
    ).all()
    if any(not f.anulada for f in intentos):
        raise Conflicto("periodo")
    intento = max((f.intento for f in intentos), default=0) + 1
    # Paso 3: insertar con su árbitro; otro id en el mismo intento es 23505 traducido.
    instante = reloj()
    with traducir(sesion, {"uq_emision_intento": "periodo"}):
        nueva = sesion.execute(
            text(
                "INSERT INTO emision (id, administracion_id, complejo_id, periodo, intento, "
                "registrada_por, request_id, registrada_en) VALUES (:id, :adm, :c, :p, :i, :por, "
                ":req, :en) ON CONFLICT (id) DO NOTHING RETURNING id"
            ),
            {
                "id": emision_id,
                "adm": administracion,
                "c": complejo_id,
                "p": periodo,
                "i": intento,
                "por": identidad.persona_id,
                "req": request_id,
                "en": instante,
            },
        ).scalar_one_or_none()
    if nueva is None:
        repetida = _replay(sesion, emision_id, complejo_id, periodo, obligaciones)
        if repetida is None:
            raise RuntimeError("el movimiento que ganó la carrera no se pudo leer")
        return repetida
    # Paso 4: cuentas en una sentencia ordenada, candados, un solo bloqueo, obligaciones.
    cuentas = crear_cuentas_de_unidades(
        sesion, complejo_id=complejo_id, unidad_ids=[o.unidad_id for o in obligaciones]
    )
    bloquear_cuentas(sesion, list(cuentas.values()))
    for o in sorted(obligaciones, key=lambda x: x.unidad_id):
        sesion.execute(
            text(
                "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, "
                "emision_id, "
                "periodo, vencimiento, ordinaria, fondo_de_reserva, extraordinaria, registrada_en) "
                "VALUES (:id, :adm, :c, :cuenta, :e, :p, :v, :o, :f, :x, :en) "
                "ON CONFLICT (administracion_id, emision_id, cuenta_id) "
                "WHERE emision_id IS NOT NULL "
                "DO NOTHING"
            ),
            {
                "id": uuid4(),
                "adm": administracion,
                "c": complejo_id,
                "cuenta": cuentas[o.unidad_id],
                "e": emision_id,
                "p": periodo,
                "v": o.vencimiento,
                "o": o.ordinaria.a_texto(),
                "f": o.fondo_de_reserva.a_texto(),
                "x": o.extraordinaria.a_texto(),
                "en": instante,
            },
        )
    corrida = uuid4()
    saldo: dict[UUID, Dinero] = {}
    for cuenta in sorted(cuentas.values()):
        imputar_pendientes(sesion, cuenta, corrida, instante)
        saldo[cuenta] = foto(sesion, cuenta).estado.deuda_sin_emision(emision_id)
    return EmisionRegistrada(emision_id, intento, cuentas, saldo)


def anular_emision(
    sesion: Session,
    identidad: Identidad,
    *,
    emision_id: UUID,
    motivo: str,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> None:
    """Agrega el evento y nada más: el efecto se calcula (D8). No bloquea ni audita: el 7 audita
    en la misma transacción (D9). Una segunda anulación es `Conflicto` siempre (R17)."""
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    limpio = normalizar_motivo(motivo)
    fila = sesion.execute(
        text("SELECT complejo_id FROM emision WHERE id = :id"), {"id": emision_id}
    ).one_or_none()
    if fila is None:
        raise NoEncontrado
    nuevo = sesion.execute(
        text(
            "INSERT INTO evento_de_emision (id, administracion_id, complejo_id, emision_id, tipo, "
            "motivo, persona_id, request_id, registrado_en) VALUES (:id, :adm, :c, :e, 'anulada', "
            ":motivo, :persona, :req, :en) "
            "ON CONFLICT (administracion_id, emision_id, tipo) DO NOTHING RETURNING id"
        ),
        {
            "id": uuid4(),
            "adm": administracion,
            "c": fila.complejo_id,
            "e": emision_id,
            "motivo": limpio,
            "persona": identidad.persona_id,
            "req": request_id,
            "en": reloj(),
        },
    ).scalar_one_or_none()
    if nuevo is None:
        raise Conflicto("emision_id")
