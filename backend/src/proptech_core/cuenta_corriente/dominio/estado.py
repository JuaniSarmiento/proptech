"""El estado de una cuenta y lo que no cuenta (D8, E7), sin base.

Nada de lo que se calcula acá persiste: el libro guarda hechos (movimientos e imputaciones) y el
estado se deriva cada vez.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Deuda

_CERO = Dinero("0.00")

#: D-086: los créditos que van a un destino fijo; los demás, con R04.
TIPOS_DE_DESTINO_FIJO = frozenset({"condonacion", "ajuste_de_interes", "bonificacion"})

Clave = tuple[UUID, Componente]


@dataclass(frozen=True)
class Obligacion:
    id: UUID
    emision_id: UUID | None
    periodo: date
    vencimiento: date
    ordinaria: Dinero
    fondo_de_reserva: Dinero
    extraordinaria: Dinero

    def capital(self) -> dict[Componente, Dinero]:
        return {
            Componente.INTERES: _CERO,
            Componente.ORDINARIA: self.ordinaria,
            Componente.FONDO_DE_RESERVA: self.fondo_de_reserva,
            Componente.EXTRAORDINARIA: self.extraordinaria,
        }


@dataclass(frozen=True)
class Movimiento:
    id: UUID
    tipo: str
    sentido: str
    importe: Dinero
    fecha_valor: date
    registrado_en: datetime
    obligacion_id: UUID | None = None
    componente: Componente | None = None
    emision_id: UUID | None = None
    corrige_a: UUID | None = None
    enlazado_a: UUID | None = None


@dataclass(frozen=True)
class ImputacionRegistrada:
    movimiento_id: UUID
    obligacion_id: UUID
    componente: Componente
    importe: Dinero
    orden: int


@dataclass(frozen=True)
class EstadoDeCuenta:
    obligaciones: tuple[Obligacion, ...]
    obligaciones_que_cuentan: frozenset[UUID]
    movimientos_que_cuentan: frozenset[UUID]
    debido: dict[Clave, Dinero]
    imputado: dict[Clave, Dinero]
    residual: dict[Clave, Dinero]
    a_favor_por_credito: dict[UUID, Dinero]
    retenidos: frozenset[UUID]
    deuda: Dinero
    credito_a_favor: Dinero
    credito_a_favor_aplicable: Dinero
    credito_a_favor_retenido: Dinero
    _por_id: dict[UUID, Obligacion] = field(default_factory=dict, repr=False)

    def deudas(self) -> list[Deuda]:
        """Lo pendiente, en la forma que consume `imputar`."""
        return [
            Deuda(obligacion, componente, o.periodo, o.vencimiento, residual)
            for (obligacion, componente), residual in self.residual.items()
            if residual > _CERO
            for o in (self._por_id[obligacion],)
        ]

    def deuda_sin_emision(self, emision_id: UUID) -> Dinero:
        """Saldo anterior (D12): residual no negativo sin las obligaciones de esa emisión."""
        total = _CERO
        for (obligacion, _), residual in self.residual.items():
            if self._por_id[obligacion].emision_id != emision_id:
                total = total + residual
        return total


def _sumar(montos: Iterable[Dinero]) -> Dinero:
    total = _CERO
    for monto in montos:
        total = total + monto
    return total


def _excluidos(
    obligaciones_que_cuentan: set[UUID],
    movimientos: dict[UUID, Movimiento],
    anuladas: set[UUID],
) -> set[UUID]:
    excluidos = {m.id for m in movimientos.values() if m.emision_id in anuladas}
    # Pares de contra-asiento, desde el extremo de cada cadena (sin corrección entrante) hacia el
    # original: I, C1 corrige I, C2 corrige C1 excluye C2/C1 y restaura I (orden topológico).
    corregidos = {m.corrige_a for m in movimientos.values() if m.corrige_a is not None}
    for extremo in movimientos.values():
        if extremo.corrige_a is None or extremo.id in corregidos:
            continue
        actual: Movimiento | None = extremo
        while actual is not None and actual.corrige_a in movimientos:
            blanco = movimientos[actual.corrige_a]
            excluidos |= {actual.id, blanco.id}
            siguiente = blanco.corrige_a
            actual = movimientos.get(siguiente) if siguiente is not None else None
    # Un débito sobre una obligación que no cuenta (el interés de una emisión anulada) no cuenta.
    for m in movimientos.values():
        if (
            m.sentido == "debito"
            and m.obligacion_id is not None
            and m.obligacion_id not in obligaciones_que_cuentan
        ):
            excluidos.add(m.id)
    # D-085: el ajuste que compensaba un interés que no cuenta tampoco cuenta.
    for m in movimientos.values():
        if (
            m.tipo == "ajuste_de_interes"
            and m.enlazado_a is not None
            and (m.enlazado_a in excluidos or m.enlazado_a not in movimientos)
        ):
            excluidos.add(m.id)
    return excluidos


def calcular_estado(
    obligaciones: Iterable[Obligacion],
    movimientos: Iterable[Movimiento],
    imputaciones: Iterable[ImputacionRegistrada],
    emisiones_anuladas: Iterable[UUID],
) -> EstadoDeCuenta:
    lista = tuple(obligaciones)
    por_id = {o.id: o for o in lista}
    anuladas = set(emisiones_anuladas)
    por_mov = {m.id: m for m in movimientos}
    obligaciones_que_cuentan = {o.id for o in lista if o.emision_id not in anuladas}
    excluidos = _excluidos(obligaciones_que_cuentan, por_mov, anuladas)
    cuentan = {i for i in por_mov if i not in excluidos}

    # Paso 2: lo que se debe por obligación y componente.
    debido: dict[Clave, Dinero] = {}
    for o in lista:
        if o.id in obligaciones_que_cuentan:
            for componente, monto in o.capital().items():
                debido[(o.id, componente)] = monto
    for m in por_mov.values():
        if (
            m.id in cuentan
            and m.sentido == "debito"
            and m.obligacion_id in obligaciones_que_cuentan
            and m.componente is not None
        ):
            clave = (m.obligacion_id, m.componente)
            debido[clave] = debido.get(clave, _CERO) + m.importe

    # Paso 3: lo imputado cuenta en orden ascendente hasta el tope; el exceso vuelve a su crédito,
    # de la imputación más reciente a la más antigua (E7).
    imputado: dict[Clave, Dinero] = {clave: _CERO for clave in debido}
    imputado_por_credito: dict[UUID, Dinero] = {}
    for i in sorted(imputaciones, key=lambda x: x.orden):
        clave = (i.obligacion_id, i.componente)
        if i.movimiento_id not in cuentan or clave not in debido:
            continue
        cabe = debido[clave] - imputado[clave]
        parte = min(i.importe, cabe) if cabe > _CERO else _CERO
        imputado[clave] = imputado[clave] + parte
        imputado_por_credito[i.movimiento_id] = (
            imputado_por_credito.get(i.movimiento_id, _CERO) + parte
        )

    # Paso 4: residual.
    residual = {clave: debido[clave] - imputado[clave] for clave in debido}

    # Paso 5: crédito a favor por crédito, aplicable o retenido.
    a_favor: dict[UUID, Dinero] = {}
    retenidos: set[UUID] = set()
    for m in por_mov.values():
        if m.id not in cuentan or m.sentido != "credito":
            continue
        a_favor[m.id] = m.importe - imputado_por_credito.get(m.id, _CERO)
        if m.tipo in TIPOS_DE_DESTINO_FIJO and a_favor[m.id] > _CERO:
            destino = (m.obligacion_id, m.componente)
            if destino not in residual or not residual[destino] > _CERO:
                retenidos.add(m.id)
    total_a_favor = _sumar(a_favor.values())
    retenido = _sumar(a_favor[i] for i in retenidos)
    return EstadoDeCuenta(
        obligaciones=lista,
        obligaciones_que_cuentan=frozenset(obligaciones_que_cuentan),
        movimientos_que_cuentan=frozenset(cuentan),
        debido=debido,
        imputado=imputado,
        residual=residual,
        a_favor_por_credito=a_favor,
        retenidos=frozenset(retenidos),
        deuda=_sumar(residual.values()),
        credito_a_favor=total_a_favor,
        credito_a_favor_aplicable=total_a_favor - retenido,
        credito_a_favor_retenido=retenido,
        _por_id=por_id,
    )
