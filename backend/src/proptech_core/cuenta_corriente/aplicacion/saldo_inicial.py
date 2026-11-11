"""Registro del saldo inicial (R09, design D5 del 4c). Lo llama el 5, que autoriza y audita.

Una sola carga por edificio, mientras su migración está pendiente. El pedido se valida entero antes
de escribir (`normalizar_pedido`), se firma, y el replay se resuelve por esa firma antes de mirar el
estado de migración. Lo escrito va en un SAVEPOINT: un rechazo posterior (una unidad de otro
edificio, una carga que ganó la carrera) deja el libro como estaba y la transacción usable.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.dinero import Dinero
from proptech_core.complejos.aplicacion.lectura import cargar_complejo
from proptech_core.cuenta_corriente.aplicacion.creditos import hoy, imputar_pendientes
from proptech_core.cuenta_corriente.aplicacion.cuentas import (
    bloquear_cuentas,
    crear_cuentas_de_unidades,
    exigir_identidad,
)
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    NoEncontrado,
    exigir_transaccion,
    traducir,
)
from proptech_core.cuenta_corriente.dominio.saldo_inicial import (
    DeudaAMigrar,
    FilaDeCredito,
    FilaDeDeuda,
    FilaDeTotal,
    OrigenDeCarga,
    PedidoNormalizado,
    SaldoDeUnidad,
    TotalesDeSaldoInicial,
    UnidadDeSaldoInicial,
    agrupar_unidad,
    firmar_pedido,
    normalizar_pedido,
    sumar_totales,
)

__all__ = [
    "FilaDeCredito",
    "FilaDeDeuda",
    "FilaDeTotal",
    "OrigenDeCarga",
    "SaldoInicialRegistrado",
    "TotalesDeSaldoInicial",
    "UnidadDeSaldoInicial",
    "registrar_saldo_inicial",
]

_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))


@dataclass(frozen=True)
class SaldoInicialRegistrado:
    operacion_id: UUID
    carga_id: UUID  # id de la fila de `carga_de_saldo_inicial`
    cuentas: dict[UUID, UUID]  # unidad -> cuenta
    por_unidad: dict[UUID, TotalesDeSaldoInicial]
    total: TotalesDeSaldoInicial  # del edificio: la suma de `por_unidad`


def _resultado(
    operacion_id: UUID,
    carga_id: UUID,
    cuentas: dict[UUID, UUID],
    saldos: Sequence[SaldoDeUnidad],
) -> SaldoInicialRegistrado:
    por_unidad = {s.unidad_id: s.totales for s in saldos}
    return SaldoInicialRegistrado(
        operacion_id, carga_id, cuentas, por_unidad, sumar_totales(list(por_unidad.values()))
    )


def _replay(
    sesion: Session, operacion_id: UUID, firma: str, saldos: Sequence[SaldoDeUnidad]
) -> SaldoInicialRegistrado | None:
    """Misma operación y misma firma: lo registrado, sin escribir, aunque la migración ya no esté
    pendiente. Otra firma: conflicto. No compara contra el libro: agrupar pierde el aporte de cada
    fila (E16), así que el pedido se compara por su firma."""
    previa = sesion.execute(
        text("SELECT id, firma_del_pedido FROM carga_de_saldo_inicial WHERE operacion_id = :op"),
        {"op": operacion_id},
    ).one_or_none()
    if previa is None:
        return None
    if previa.firma_del_pedido != firma:
        raise Conflicto("operacion_id")
    filas = sesion.execute(
        text("SELECT unidad_id, id FROM cuenta WHERE unidad_id = ANY(:ids)").bindparams(_IDS),
        {"ids": [s.unidad_id for s in saldos]},
    ).all()
    cuentas = {UUID(str(f.unidad_id)): UUID(str(f.id)) for f in filas}
    return _resultado(operacion_id, UUID(str(previa.id)), cuentas, saldos)


def _insertar_carga(
    sesion: Session,
    identidad: Identidad,
    *,
    administracion: UUID,
    pedido: PedidoNormalizado,
    firma: str,
    operacion_id: UUID,
    request_id: UUID,
    instante: datetime,
) -> UUID | None:
    """`None`: otra transacción ya registró este `operacion_id` (se resuelve como replay)."""
    with traducir(sesion, {"uq_carga_complejo": "complejo_id"}):
        nueva = sesion.execute(
            text(
                "INSERT INTO carga_de_saldo_inicial (id, administracion_id, complejo_id, "
                "operacion_id, fecha_de_migracion, origen, archivo, motivo, firma_del_pedido, "
                "registrado_por, request_id, registrado_en) VALUES (:id, :adm, :complejo, :op, "
                ":fecha, :origen, :archivo, :motivo, :firma, :por, :req, :en) "
                "ON CONFLICT (administracion_id, operacion_id) DO NOTHING RETURNING id"
            ),
            {
                "id": uuid4(),
                "adm": administracion,
                "complejo": pedido.complejo_id,
                "op": operacion_id,
                "fecha": pedido.fecha_de_migracion,
                "origen": pedido.origen.tipo,
                "archivo": pedido.origen.archivo,
                "motivo": pedido.origen.motivo,
                "firma": firma,
                "por": identidad.persona_id,
                "req": request_id,
                "en": instante,
            },
        ).scalar_one_or_none()
    return None if nueva is None else UUID(str(nueva))


def _insertar_obligacion(
    sesion: Session,
    *,
    administracion: UUID,
    complejo_id: UUID,
    cuenta: UUID,
    operacion_id: UUID,
    deuda: DeudaAMigrar,
    instante: datetime,
) -> UUID:
    identificador = uuid4()
    sesion.execute(
        text(
            "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, operacion_id, "
            "periodo, vencimiento, ordinaria, fondo_de_reserva, extraordinaria, registrada_en) "
            "VALUES (:id, :adm, :c, :cuenta, :op, :p, :v, :o, :f, :x, :en)"
        ),
        {
            "id": identificador,
            "adm": administracion,
            "c": complejo_id,
            "cuenta": cuenta,
            "op": operacion_id,
            "p": deuda.periodo,
            "v": deuda.vencimiento,
            "o": deuda.ordinaria.a_texto(),
            "f": deuda.fondo_de_reserva.a_texto(),
            "x": deuda.extraordinaria.a_texto(),
            "en": instante,
        },
    )
    return identificador


def _insertar_interes_importado(
    sesion: Session,
    identidad: Identidad,
    *,
    administracion: UUID,
    complejo_id: UUID,
    cuenta: UUID,
    obligacion: UUID,
    importe: Dinero,
    corte: date,
    request_id: UUID,
    instante: datetime,
) -> UUID:
    """Un débito de `interes` con corte en la migración, sin emisión ni tramos: entra tal cual y no
    forma parte de la base de ningún interés posterior (R03, D-082, D-083)."""
    identificador = uuid4()
    sesion.execute(
        text(
            "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, sentido, "
            "importe, fecha_valor, registrado_por, request_id, registrado_en, obligacion_id, "
            "componente, corte) VALUES (:id, :adm, :c, :cuenta, 'interes', 'debito', :importe, "
            ":corte, :por, :req, :en, :obl, 'interes', :corte)"
        ),
        {
            "id": identificador,
            "adm": administracion,
            "c": complejo_id,
            "cuenta": cuenta,
            "importe": importe.a_texto(),
            "corte": corte,
            "por": identidad.persona_id,
            "req": request_id,
            "en": instante,
            "obl": obligacion,
        },
    )
    return identificador


def _insertar_credito(
    sesion: Session,
    identidad: Identidad,
    *,
    administracion: UUID,
    complejo_id: UUID,
    cuenta: UUID,
    operacion_id: UUID,
    importe: Dinero,
    fecha_valor: date,
    request_id: UUID,
    instante: datetime,
) -> UUID:
    identificador = uuid4()
    sesion.execute(
        text(
            "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, sentido, "
            "importe, fecha_valor, registrado_por, request_id, registrado_en, operacion_id) "
            "VALUES (:id, :adm, :c, :cuenta, 'saldo_inicial', 'credito', :importe, :fecha, :por, "
            ":req, :en, :op)"
        ),
        {
            "id": identificador,
            "adm": administracion,
            "c": complejo_id,
            "cuenta": cuenta,
            "importe": importe.a_texto(),
            "fecha": fecha_valor,
            "por": identidad.persona_id,
            "req": request_id,
            "en": instante,
            "op": operacion_id,
        },
    )
    return identificador


def _insertar_origenes(
    sesion: Session,
    *,
    administracion: UUID,
    complejo_id: UUID,
    carga_id: UUID,
    cuenta: UUID,
    ligas: set[tuple[int | None, UUID, str | None, bool]],
) -> None:
    """Cada fila liga lo que formó: `(fila, referencia, sentido, es_obligacion)`. Sin repetidos
    (varias filas manuales sin número ligan lo mismo una sola vez)."""
    for fila, referencia, sentido, es_obligacion in sorted(
        ligas, key=lambda x: (x[0] is not None, x[0] or 0, str(x[1]))
    ):
        sesion.execute(
            text(
                "INSERT INTO origen_de_saldo_inicial (id, administracion_id, complejo_id, "
                "carga_id, cuenta_id, fila, obligacion_id, movimiento_id, "
                "sentido_del_movimiento) VALUES (:id, :adm, :c, :carga, :cuenta, :fila, :obl, "
                ":mov, :sentido)"
            ),
            {
                "id": uuid4(),
                "adm": administracion,
                "c": complejo_id,
                "carga": carga_id,
                "cuenta": cuenta,
                "fila": fila,
                "obl": referencia if es_obligacion else None,
                "mov": None if es_obligacion else referencia,
                "sentido": sentido,
            },
        )


def registrar_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    operacion_id: UUID,
    fecha_de_migracion: date,
    origen: OrigenDeCarga,
    unidades: Sequence[UnidadDeSaldoInicial],
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> SaldoInicialRegistrado:
    exigir_transaccion(sesion)
    administracion = exigir_identidad(sesion, identidad)
    instante = reloj()
    # Validar todo antes de escribir; la fecha de "hoy" es la del reloj, en Mendoza.
    pedido = normalizar_pedido(
        complejo_id=complejo_id,
        fecha_de_migracion=fecha_de_migracion,
        origen=origen,
        unidades=tuple(unidades),
        hoy=hoy(lambda: instante),
    )
    firma = firmar_pedido(pedido)
    saldos = [agrupar_unidad(u, pedido.fecha_de_migracion) for u in pedido.unidades]
    # Replay por `operacion_id`, antes del estado de migración (D5).
    previo = _replay(sesion, operacion_id, firma, saldos)
    if previo is not None:
        return previo
    edificio = cargar_complejo(sesion, complejo_id)  # D-116: el estado lo lee `complejos`
    if edificio is None:
        raise NoEncontrado
    if edificio.estado_migracion != "pendiente":
        raise Conflicto("estado_migracion")
    with sesion.begin_nested():
        carga = _insertar_carga(
            sesion,
            identidad,
            administracion=administracion,
            pedido=pedido,
            firma=firma,
            operacion_id=operacion_id,
            request_id=request_id,
            instante=instante,
        )
        if carga is None:  # perdió la carrera contra el mismo `operacion_id`
            repetida = _replay(sesion, operacion_id, firma, saldos)
            if repetida is None:
                raise RuntimeError("la carga que ganó la carrera no se pudo leer")
            return repetida
        cuentas = crear_cuentas_de_unidades(
            sesion, complejo_id=complejo_id, unidad_ids=[s.unidad_id for s in saldos]
        )
        bloquear_cuentas(sesion, sorted(cuentas.values()))
        con_credito: list[UUID] = []
        for saldo in saldos:
            cuenta = cuentas[saldo.unidad_id]
            ligas: set[tuple[int | None, UUID, str | None, bool]] = set()
            for deuda in saldo.deudas:
                obligacion = _insertar_obligacion(
                    sesion,
                    administracion=administracion,
                    complejo_id=complejo_id,
                    cuenta=cuenta,
                    operacion_id=operacion_id,
                    deuda=deuda,
                    instante=instante,
                )
                ligas |= {(f, obligacion, None, True) for f in deuda.filas_de_capital}
                if deuda.interes_importado.decimal > 0:
                    interes = _insertar_interes_importado(
                        sesion,
                        identidad,
                        administracion=administracion,
                        complejo_id=complejo_id,
                        cuenta=cuenta,
                        obligacion=obligacion,
                        importe=deuda.interes_importado,
                        corte=pedido.fecha_de_migracion,
                        request_id=request_id,
                        instante=instante,
                    )
                    ligas |= {(f, interes, "debito", False) for f in deuda.filas_de_interes}
            if saldo.credito.decimal > 0:
                movimiento = _insertar_credito(
                    sesion,
                    identidad,
                    administracion=administracion,
                    complejo_id=complejo_id,
                    cuenta=cuenta,
                    operacion_id=uuid5(operacion_id, str(saldo.unidad_id)),
                    importe=saldo.credito,
                    fecha_valor=pedido.fecha_de_migracion,
                    request_id=request_id,
                    instante=instante,
                )
                ligas |= {(f, movimiento, "credito", False) for f in saldo.filas_de_credito}
                con_credito.append(cuenta)
            _insertar_origenes(
                sesion,
                administracion=administracion,
                complejo_id=complejo_id,
                carga_id=carga,
                cuenta=cuenta,
                ligas=ligas,
            )
        corrida = uuid4()
        for cuenta in con_credito:
            imputar_pendientes(sesion, cuenta, corrida, instante)
        return _resultado(operacion_id, carga, cuentas, saldos)
