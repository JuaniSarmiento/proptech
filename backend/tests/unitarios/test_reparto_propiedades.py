"""Oráculo racional independiente: no comparte la aritmética entera de producción."""

from decimal import Decimal
from fractions import Fraction
from uuid import UUID

from hypothesis import example, given
from hypothesis import strategies as st

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.reparto import ParteARepartir, clave_de_orden_natural, repartir


@st.composite
def casos(draw: st.DrawFn) -> tuple[int, list[int]]:
    n = draw(st.integers(2, 8))
    # Ambos caminos fuerzan empates; el tercero recorre seis decimales y pesos cero.
    pesos = draw(
        st.one_of(
            st.lists(st.sampled_from([250000, 500000, 1000000]), min_size=n, max_size=n),
            st.integers(1, 1000000).map(lambda p: [p] * n),
            st.lists(st.integers(0, 1000000), min_size=n, max_size=n).filter(any),
        )
    )
    total = draw(
        st.one_of(
            st.integers(-99999999999999, 99999999999999),
            st.sampled_from([1, 5, 200, 99999999999999]),
        )
    )
    return total, pesos


def calcular(total: int, pesos: list[int]) -> tuple[list[Fraction], list[Fraction]]:
    partes = [
        ParteARepartir(
            str(i),
            Decimal(p) / Decimal(1000000),
            clave_de_orden_natural(("A" if i % 2 else "") + str(i), UUID(int=i)),
        )
        for i, p in enumerate(pesos)
    ]
    signo = "-" if total < 0 else ""
    resultado = repartir(Dinero(f"{signo}{abs(total) // 100}.{abs(total) % 100:02d}"), partes)
    actual = [abs(Fraction(resultado[str(i)].decimal)) for i in range(len(pesos))]
    exacto = [Fraction(abs(total), 100) * Fraction(p, sum(pesos)) for p in pesos]
    return actual, exacto


@example((200, [1000000, 1000000, 1000000]))
@given(casos())
def test_propiedad_suma(caso: tuple[int, list[int]]) -> None:
    total, pesos = caso
    actual, _ = calcular(total, pesos)
    assert sum(actual) == Fraction(abs(total), 100)


@example((200, [1000000, 1000000]))
@given(casos())
def test_propiedad_distancia(caso: tuple[int, list[int]]) -> None:
    actual, exacto = calcular(*caso)
    assert all(abs(a - e) < Fraction(1, 100) for a, e in zip(actual, exacto, strict=True))


@example((5, [600000, 250000, 150000]))
@given(casos())
def test_propiedad_restos(caso: tuple[int, list[int]]) -> None:
    actual, exacto = calcular(*caso)
    # floor racional del oráculo, independiente de divmod entero de producción.
    truncados = [Fraction(e // Fraction(1, 100), 100) for e in exacto]
    con_extra = [i for i, a in enumerate(actual) if a > truncados[i]]
    sin_extra = [i for i, a in enumerate(actual) if a == truncados[i]]
    assert all(
        exacto[i] - truncados[i] >= exacto[j] - truncados[j] for i in con_extra for j in sin_extra
    )


@example((1, [1000000, 1000000]))
@given(casos())
def test_propiedad_orden(caso: tuple[int, list[int]]) -> None:
    total, pesos = caso
    partes = [
        ParteARepartir(str(i), Decimal(p) / Decimal(1000000), (i,)) for i, p in enumerate(pesos)
    ]
    signo = "-" if total < 0 else ""
    monto = Dinero(f"{signo}{abs(total) // 100}.{abs(total) % 100:02d}")
    assert repartir(monto, partes) == repartir(monto, list(reversed(partes)))
