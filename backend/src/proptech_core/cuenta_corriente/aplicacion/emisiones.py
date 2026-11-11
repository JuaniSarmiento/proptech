"""Emisión y anulación (D4, E3, R17). Lo llama el 7, que autoriza y audita."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.complejos.aplicacion.lectura import configuracion_vigente
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
from proptech_core.cuenta_corriente.aplicacion.lecturas import FotoDeCuenta, fotos
from proptech_core.cuenta_corriente.dominio.errores import (
    EntradaInvalida as EntradaInvalidaDeDominio,
)
from proptech_core.cuenta_corriente.dominio.intereses import (
    ConfiguracionDeInteres,
    FormaDeCalculo,
    InteresCalculado,
    calcular_intereses,
)

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
class InteresDeEmision:
    """Un débito de interés con el `emision_id` de la emisión (D1): cuente o no hoy."""

    obligacion_id: UUID
    corte: date
    importe: Dinero


@dataclass(frozen=True)
class EmisionRegistrada:
    emision_id: UUID
    intento: int
    cuentas: dict[UUID, UUID]  # unidad -> cuenta de las obligaciones de la emisión
    #: D12, R06: la foto que el 7 publica, tomada bajo el candado después de imputar pendientes.
    #: Cubre las cuentas alcanzadas (D0): las de sus obligaciones y las que sólo recibieron interés.
    saldo_anterior: dict[UUID, Dinero]  # cuenta -> saldo anterior
    #: D1: por cuenta, los intereses de esta emisión, leídos del libro (replay: también los que ya
    #: no cuentan). Una cuenta sin interés de la emisión no figura.
    intereses: dict[UUID, tuple[InteresDeEmision, ...]] = field(default_factory=dict)


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


def _cuentas_alcanzadas(sesion: Session, emision_id: UUID) -> list[UUID]:
    """D0: las cuentas con una obligación de la emisión más las que tienen un movimiento suyo (en
    el 4c, su interés). Fija desde que la emisión se confirma: sólo `registrar_emision`, dentro de
    su transacción, escribe movimientos con `emision_id`."""
    filas = (
        sesion.execute(
            text(
                "SELECT cuenta_id FROM obligacion WHERE emision_id = :id "
                "UNION SELECT cuenta_id FROM movimiento WHERE emision_id = :id"
            ),
            {"id": emision_id},
        )
        .scalars()
        .all()
    )
    return sorted(UUID(str(c)) for c in filas)


def _intereses_de(
    emision_id: UUID, actuales: dict[UUID, FotoDeCuenta]
) -> dict[UUID, tuple[InteresDeEmision, ...]]:
    por_cuenta: dict[UUID, tuple[InteresDeEmision, ...]] = {}
    for cuenta, actual in actuales.items():
        propios = tuple(
            InteresDeEmision(m.obligacion_id, m.corte, m.importe)
            for m in actual.movimientos.values()
            if m.tipo == "interes"
            and m.sentido == "debito"
            and m.emision_id == emision_id
            and m.obligacion_id is not None
            and m.corte is not None
        )
        if propios:
            por_cuenta[cuenta] = tuple(
                sorted(propios, key=lambda i: (str(i.obligacion_id), i.corte))
            )
    return por_cuenta


def _registrar_intereses(
    sesion: Session,
    identidad: Identidad,
    *,
    administracion: UUID,
    complejo_id: UUID,
    emision_id: UUID,
    corte: date,
    cuentas: list[UUID],
    request_id: UUID,
    instante: datetime,
) -> set[UUID]:
    """D1, E2, E10: calcula y registra el interés de las cuentas de unidad ya bloqueadas, con el
    corte de la emisión. Devuelve las cuentas que recibieron alguno."""
    actuales = fotos(sesion, cuentas)
    if not any(
        o.vencimiento < corte and o.id in a.estado.obligaciones_que_cuentan
        for a in actuales.values()
        for o in a.estado.obligaciones
    ):
        return set()
    version = configuracion_vigente(sesion, complejo_id, corte)
    if version is None:
        raise Conflicto("configuracion")
    configuracion = ConfiguracionDeInteres(
        Porcentaje(version["tasa_mensual"]),
        int(version["dias_de_gracia"]),
        _forma(version["forma_de_calculo"]),
    )
    recibieron: set[UUID] = set()
    for cuenta in sorted(actuales):
        actual = actuales[cuenta]
        try:
            # Todos los movimientos, también los anulados o contra-asentados: sin ellos no se
            # aplica E1 y se choca con `uq_mov_interes`.
            calculados = calcular_intereses(
                actual.estado, actual.movimientos.values(), corte, configuracion
            )
        except EntradaInvalidaDeDominio:
            # Mes entero con días de un mes que no son un bloque contiguo: no hay interés coherente
            # que cobrar. Se rechaza la emisión entera (lo registrado vuelve con el SAVEPOINT) en
            # vez de saltear la obligación: callar un interés es perder plata sin aviso.
            raise Conflicto("interes") from None
        for interes in calculados:
            _insertar_interes(
                sesion,
                identidad,
                administracion=administracion,
                actual=actual,
                emision_id=emision_id,
                interes=interes,
                version=version,
                request_id=request_id,
                instante=instante,
            )
            recibieron.add(cuenta)
    return recibieron


def _forma(valor: Any) -> FormaDeCalculo:
    if valor == "mes_entero":
        return "mes_entero"
    if valor == "proporcional_por_dia":
        return "proporcional_por_dia"
    raise Conflicto("configuracion")


def _insertar_interes(
    sesion: Session,
    identidad: Identidad,
    *,
    administracion: UUID,
    actual: FotoDeCuenta,
    emision_id: UUID,
    interes: InteresCalculado,
    version: dict[str, Any],
    request_id: UUID,
    instante: datetime,
) -> None:
    movimiento = uuid4()
    sesion.execute(
        text(
            "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, sentido, "
            "importe, fecha_valor, registrado_por, request_id, registrado_en, emision_id, "
            "obligacion_id, componente, corte) VALUES (:id, :adm, :complejo, :cuenta, 'interes', "
            "'debito', :importe, :corte, :por, :req, :en, :emision, :obl, 'interes', :corte)"
        ),
        {
            "id": movimiento,
            "adm": administracion,
            "complejo": actual.complejo_id,
            "cuenta": actual.cuenta_id,
            "importe": interes.importe.a_texto(),
            "corte": interes.corte,
            "por": identidad.persona_id,
            "req": request_id,
            "en": instante,
            "emision": emision_id,
            "obl": interes.obligacion_id,
        },
    )
    for tramo in interes.tramos:
        sesion.execute(
            text(
                "INSERT INTO tramo_de_interes (id, administracion_id, complejo_id, cuenta_id, "
                "movimiento_id, sentido_del_movimiento, desde, hasta, dias, base, tasa_mensual, "
                "forma_de_calculo, dias_de_gracia, configuracion_id, registrado_en) "
                "VALUES (:id, :adm, :complejo, :cuenta, :mov, 'debito', :desde, :hasta, :dias, "
                ":base, :tasa, :forma, :gracia, :version, :en)"
            ),
            {
                "id": uuid4(),
                "adm": administracion,
                "complejo": actual.complejo_id,
                "cuenta": actual.cuenta_id,
                "mov": movimiento,
                "desde": tramo.desde,
                "hasta": tramo.hasta,
                "dias": tramo.dias,
                "base": tramo.base.a_texto(),
                "tasa": version["tasa_mensual"],
                "forma": version["forma_de_calculo"],
                "gracia": int(version["dias_de_gracia"]),
                "version": version["id"],
                "en": instante,
            },
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
    # RB4B-05, E15: el libro no persiste la foto del saldo anterior (la guarda el 7); el replay la
    # vuelve a calcular sin imputar. CX-02, E12, D0: las cuentas alcanzadas, bloqueadas en un solo
    # pedido antes de una sola foto SQL; la anulación toma los mismos candados (RF-01), así que se
    # ve entera o no se ve. Los intereses se leen del libro, cuenten o no hoy: nunca se recalculan.
    alcanzadas = _cuentas_alcanzadas(sesion, emision_id)
    bloquear_cuentas(sesion, alcanzadas)
    actuales = fotos(sesion, alcanzadas)
    saldo = {
        cuenta: actual.estado.deuda_sin_emision(emision_id) for cuenta, actual in actuales.items()
    }
    return EmisionRegistrada(
        emision_id, fila.intento, cuentas, saldo, _intereses_de(emision_id, actuales)
    )


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
    # Paso 2: intentos y anulaciones del período, antes de insertar.
    intentos = sesion.execute(
        text(
            "SELECT e.intento, EXISTS (SELECT 1 FROM evento_de_emision v WHERE v.emision_id = e.id "
            "AND v.tipo = 'anulada') AS anulada FROM emision e "
            "WHERE e.complejo_id = :c AND e.periodo = :p"
        ),
        {"c": complejo_id, "p": periodo},
    ).all()
    # CX-01, E4: una emisión idéntica pudo confirmarse entre el primer replay y esta lectura.
    # Su replay toma los candados antes de calcular el saldo; precede al rechazo por período.
    previo = _replay(sesion, emision_id, complejo_id, periodo, obligaciones)
    if previo is not None:
        return previo
    if any(not f.anulada for f in intentos):
        raise Conflicto("periodo")
    intento = max((f.intento for f in intentos), default=0) + 1
    # Pasos 3 y 4 en un SAVEPOINT (RB4B-03): un error del paso 4 (la unidad ajena, que rechaza la
    # FK después de insertar la emisión) no deja una emisión sin obligaciones tomando el período.
    with sesion.begin_nested():
        # Paso 3: insertar con su árbitro; otro id en el mismo intento es 23505 traducido.
        instante = reloj()
        # E11: sin nombrar `complejo` en el SQL del libro; la FK lo rechaza (NoEncontrado).
        with traducir(sesion, {"uq_emision_intento": "periodo"}):
            nueva = sesion.execute(
                text(
                    "INSERT INTO emision (id, administracion_id, complejo_id, periodo, intento, "
                    "registrada_por, request_id, registrada_en) "
                    "VALUES (:id, :adm, :c, :p, :i, :por, :req, :en) "
                    "ON CONFLICT (id) DO NOTHING RETURNING id"
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
        # E10: todas las cuentas de unidad del edificio en un solo pedido ordenado, también las que
        # no emiten este mes (pueden recibir interés); las de persona quedan fuera hasta el 4d.
        de_unidad = sesion.execute(
            text("SELECT id FROM cuenta WHERE complejo_id = :c AND unidad_id IS NOT NULL"),
            {"c": complejo_id},
        ).scalars()
        edificio = {UUID(str(c)) for c in de_unidad} | set(cuentas.values())
        bloquear_cuentas(sesion, sorted(edificio))
        for o in sorted(obligaciones, key=lambda x: x.unidad_id):
            sesion.execute(
                text(
                    "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, "
                    "emision_id, periodo, vencimiento, ordinaria, fondo_de_reserva, "
                    "extraordinaria, registrada_en) "
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
        # E2: el corte es el último día del mes anterior al período que se emite.
        recibieron = _registrar_intereses(
            sesion,
            identidad,
            administracion=administracion,
            complejo_id=complejo_id,
            emision_id=emision_id,
            corte=periodo - timedelta(days=1),
            cuentas=sorted(edificio),
            request_id=request_id,
            instante=instante,
        )
        # Las cuentas alcanzadas (D0) imputan sus créditos a favor: el interés cobra primero (R04).
        alcanzadas = sorted(set(cuentas.values()) | recibieron)
        corrida = uuid4()
        for cuenta in alcanzadas:
            imputar_pendientes(sesion, cuenta, corrida, instante)
        # RF-01, E12: una sola foto SQL de todas las alcanzadas, bajo sus candados, después de
        # imputar; la anulación también los toma, así que no se mete entre lecturas.
        actuales = fotos(sesion, alcanzadas)
        saldo = {
            cuenta: actual.estado.deuda_sin_emision(emision_id)
            for cuenta, actual in actuales.items()
        }
        return EmisionRegistrada(
            emision_id, intento, cuentas, saldo, _intereses_de(emision_id, actuales)
        )


def anular_emision(
    sesion: Session,
    identidad: Identidad,
    *,
    emision_id: UUID,
    motivo: str,
    request_id: UUID,
    reloj: Reloj = ahora_utc,
) -> None:
    """Agrega el evento y nada más: el efecto se calcula (D8). No audita: el 7 audita en la misma
    transacción (D9). Una segunda anulación es `Conflicto` siempre (R17).

    Bloquea las cuentas alcanzadas por la emisión antes de escribir (RF-01, RF-02): sin el
    candado, la anulación podía confirmarse entre las lecturas del saldo anterior de otra emisión
    (foto mezclada, E12) o después del chequeo `_anulada` de una corrección y antes de su escritura
    (E6, R08). Quien anule junto con otras cuentas en la misma transacción respeta el orden de
    `bloquear_cuentas` (E2)."""
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    limpio = normalizar_motivo(motivo)
    fila = sesion.execute(
        text("SELECT complejo_id FROM emision WHERE id = :id"), {"id": emision_id}
    ).one_or_none()
    if fila is None:
        raise NoEncontrado
    # PR-02, D0: también las cuentas que sólo recibieron interés de esta emisión.
    bloquear_cuentas(sesion, _cuentas_alcanzadas(sesion, emision_id))
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
