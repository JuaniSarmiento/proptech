"""2.2 y 2.3 · Propiedades de D8 con hypothesis (QA-2, QA-10).

El oráculo suma débitos y créditos por su propio camino, con `Decimal`, y decide qué no cuenta sin
importar el predicado de producción. La identidad sola no vigila el reparto (QA-2): por eso se
exigen además los topes por componente y que las imputaciones bajen la deuda.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from hypothesis import given
from hypothesis import strategies as st

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.dominio.estado import (
    EstadoDeCuenta,
    ImputacionRegistrada,
    Movimiento,
    Obligacion,
    calcular_estado,
)
from proptech_core.cuenta_corriente.dominio.imputacion import Componente

HOY = datetime(2026, 10, 26, tzinfo=UTC)
COMPONENTES = list(Componente)
CENTAVOS = st.integers(min_value=1, max_value=100_000_000)  # $0,01 a $1.000.000,00


def plata(centavos: int) -> Dinero:
    return Dinero(f"{centavos // 100}.{centavos % 100:02d}")


@dataclass
class Caso:
    obligaciones: list[Obligacion]
    intereses: list[Movimiento]
    creditos: list[Movimiento]
    contras: list[Movimiento]
    imputaciones: list[ImputacionRegistrada]
    anuladas: set[UUID]


@st.composite
def casos(draw: st.DrawFn, *, exclusiones: bool) -> Caso:
    emisiones = [uuid4() for _ in range(3)]
    obligaciones = []
    for n in range(draw(st.integers(1, 20))):
        partes = draw(st.lists(st.integers(0, 100_000_000), min_size=3, max_size=3))
        if sum(partes) == 0:
            partes[0] = 1
        periodo = date(2026, 1 + n % 12, 1)
        obligaciones.append(
            Obligacion(
                uuid4(),
                draw(st.sampled_from(emisiones)),
                periodo,
                periodo.replace(day=10),
                *(plata(p) for p in partes),
            )
        )
    intereses = []
    if exclusiones:
        for o in obligaciones:
            if draw(st.booleans()):
                intereses.append(
                    Movimiento(
                        uuid4(),
                        "interes",
                        "debito",
                        plata(draw(CENTAVOS)),
                        date(2026, 10, 1),
                        HOY,
                        o.id,
                        Componente.INTERES,
                    )
                )
    creditos = [
        Movimiento(uuid4(), "pago", "credito", plata(c), date(2026, 10, 1), HOY)
        for c in draw(st.lists(CENTAVOS, max_size=20))
    ]
    imputaciones = []
    orden = 0
    for c in creditos:
        resto = int(c.importe.decimal * 100)
        # RB4B-01: en producción las filas de un crédito pueden sumar más que su importe (una
        # imputación vieja que revive cuando su componente vuelve a crecer, más la reimputada).
        de_mas = draw(st.booleans())
        for _ in range(draw(st.integers(0, 3))):
            if resto == 0:
                break
            parte = draw(st.integers(1, resto))
            if not de_mas:
                resto -= parte
            orden += 1
            o = draw(st.sampled_from(obligaciones))
            imputaciones.append(
                ImputacionRegistrada(
                    c.id, o.id, draw(st.sampled_from(COMPONENTES)), plata(parte), orden
                )
            )
    contras: list[Movimiento] = []
    anuladas: set[UUID] = set()
    if exclusiones:
        anuladas = set(draw(st.lists(st.sampled_from(emisiones), max_size=2)))
        for blanco in [*intereses, *creditos]:
            if draw(st.integers(0, 3)) == 0:
                sentido = "credito" if blanco.sentido == "debito" else "debito"
                contras.append(
                    Movimiento(
                        uuid4(),
                        "correccion",
                        sentido,
                        blanco.importe,
                        date(2026, 10, 2),
                        HOY,
                        corrige_a=blanco.id,
                    )
                )
    total = sum(
        (sum(o.capital().values(), start=Dinero("0.00")).decimal for o in obligaciones),
        start=Decimal(0),
    ) + sum((m.importe.decimal for m in [*intereses, *creditos, *contras]), start=Decimal(0))
    # QA-10: los generadores se acotan a $40.000.000 de suma absoluta, dentro de NUMERIC(14,2).
    if total > Decimal("40000000"):
        from hypothesis import assume

        assume(False)
    return Caso(obligaciones, intereses, creditos, contras, imputaciones, anuladas)


def oraculo(caso: Caso) -> Decimal:
    """Σ débitos que cuentan (capital incluido) menos Σ créditos que cuentan, por camino propio."""
    vivas = {o.id for o in caso.obligaciones if o.emision_id not in caso.anuladas}
    corregidos = {m.corrige_a for m in caso.contras}
    debitos = sum(
        (
            sum((p.decimal for p in o.capital().values()), start=Decimal(0))
            for o in caso.obligaciones
            if o.id in vivas
        ),
        start=Decimal(0),
    ) + sum(
        (
            m.importe.decimal
            for m in caso.intereses
            if m.id not in corregidos and m.obligacion_id in vivas
        ),
        start=Decimal(0),
    )
    creditos = sum(
        (m.importe.decimal for m in caso.creditos if m.id not in corregidos), start=Decimal(0)
    )
    return debitos - creditos


def calcular(caso: Caso) -> EstadoDeCuenta:
    return calcular_estado(
        caso.obligaciones,
        [*caso.intereses, *caso.creditos, *caso.contras],
        caso.imputaciones,
        caso.anuladas,
    )


def _topes(caso: Caso) -> None:
    e = calcular(caso)
    assert e.deuda.decimal - e.credito_a_favor.decimal == oraculo(caso)
    for clave, residual in e.residual.items():
        assert residual.decimal >= 0, f"residual negativo en {clave}"
        assert e.imputado[clave].decimal <= e.debido[clave].decimal, f"imputado > debido en {clave}"
    for credito, favor in e.a_favor_por_credito.items():
        assert favor.decimal >= 0, f"crédito a favor negativo en {credito}"


@given(casos(exclusiones=False))
def test_identidad_y_topes_sin_exclusiones(caso: Caso) -> None:
    _topes(caso)


@given(casos(exclusiones=True))
def test_identidad_y_topes_con_anulaciones_y_correcciones(caso: Caso) -> None:
    """2.3: la propiedad de 2.2 extendida con anulaciones y contra-asientos al azar."""
    _topes(caso)


@given(casos(exclusiones=False))
def test_imputaciones_que_cuentan_bajan_la_deuda(caso: Caso) -> None:
    e = calcular(caso)
    capital = sum(
        (
            sum((p.decimal for p in o.capital().values()), start=Decimal(0))
            for o in caso.obligaciones
        ),
        start=Decimal(0),
    )
    # Por el oráculo, no por lo que calculó la producción: alguna imputación cae sobre capital vivo.
    por_id = {o.id: o for o in caso.obligaciones}
    efectiva = any(
        por_id[i.obligacion_id].capital()[i.componente].decimal > 0 for i in caso.imputaciones
    )
    if efectiva:
        assert e.deuda.decimal < capital
    else:
        assert e.deuda.decimal == capital
