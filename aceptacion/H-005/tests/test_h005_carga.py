"""H-005 · C01 a C04, C08 a C11: lo que la carga deja en el libro, su origen, el replay y lo que
devuelve (spec `saldo-inicial`, design D5)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from proptech_core.cuenta_corriente.aplicacion import lecturas

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h005 import (
    AGO,
    ARCHIVO,
    MIGRACION,
    OCT,
    SEP,
    cargar,
    cargas,
    conteos,
    credito,
    cuenta_de,
    d,
    deuda,
    dia,
    filas_de,
    importado,
    leer,
    manual,
    movimientos_saldo_inicial,
    obligacion_del,
    obligaciones,
    origenes,
    poner_estado,
    total,
    totales,
    unidad,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def u(mundo: Mundo, n: int) -> UUID:
    return mundo.unidades[n]


def dos_periodos_de_u1(mundo: Mundo, *, interes_agosto: str = "0.00") -> object:
    return unidad(
        u(mundo, 1),
        deuda(7, AGO, dia(8, 10), "80000.00", interes=interes_agosto),
        deuda(8, SEP, dia(9, 10), "85000.00"),
    )


def dos_conceptos_de_u5(mundo: Mundo) -> object:
    return unidad(
        u(mundo, 5),
        deuda(12, SEP, dia(9, 10), "85000.00", interes="3000.00"),
        deuda(13, SEP, dia(9, 10), "20000.00", componente="extraordinaria"),
    )


# --- C01 · Dos períodos -----------------------------------------------------------------------


def test_c01_dos_periodos_viejos(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Dos períodos viejos"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_periodos_de_u1(mundo)])
        cuenta = cuenta_de(s, u(mundo, 1))
        obls = obligaciones(s, cuenta)
        assert [(o.periodo, o.vencimiento) for o in obls] == [(AGO, dia(8, 10)), (SEP, dia(9, 10))]
        assert all(o.emision_id is None for o in obls), "una obligación migrada no tiene emisión"
        assert sum((o.capital for o in obls), d("0.00")) == d("165000.00")
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("165000.00")


# --- C02 · Dos conceptos del mismo período ----------------------------------------------------


def test_c02_dos_conceptos_del_mismo_periodo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Dos conceptos del mismo período"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos_de_u5(mundo)])
        cuenta = cuenta_de(s, u(mundo, 5))
        obls = obligaciones(s, cuenta)
        assert len(obls) == 1, f"se espera una sola obligación de septiembre, hay {len(obls)}"
        o = obls[0]
        assert (o.periodo, o.ordinaria, o.extraordinaria, o.fondo_de_reserva) == (
            SEP,
            d("85000.00"),
            d("20000.00"),
            d("0.00"),
        )
        i = importado(s, o.id)
        assert (i.importe, i.corte) == (d("3000.00"), MIGRACION)


# --- C03 · Total único ------------------------------------------------------------------------


def test_c03_total_unico(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Total único"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [unidad(u(mundo, 2), total(20, "50000.00"), modo="total")])
        obls = obligaciones(s, cuenta_de(s, u(mundo, 2)))
        assert len(obls) == 1
        o = obls[0]
        assert (o.periodo, o.vencimiento, o.ordinaria, o.capital) == (
            OCT,
            MIGRACION,
            d("50000.00"),
            d("50000.00"),
        )


# --- C04 · Interés importado (la parte que no necesita emitir) -------------------------------


def test_c04_fila_de_solo_interes_junto_a_otra_con_capital(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Fila de sólo interés junto a otra con capital"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                unidad(
                    u(mundo, 6),
                    deuda(14, SEP, dia(9, 10), "0.00", interes="500.00"),
                    deuda(15, SEP, dia(9, 10), "10000.00"),
                )
            ],
        )
        o = obligacion_del(s, cuenta_de(s, u(mundo, 6)), SEP)
        assert o.capital == d("10000.00")
        assert importado(s, o.id).importe == d("500.00")


# --- C08 · Crédito inicial --------------------------------------------------------------------


def test_c08_unidad_con_saldo_a_favor(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Unidad con saldo a favor"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [unidad(u(mundo, 3), credito(30, "3000.00"))])
        cuenta = cuenta_de(s, u(mundo, 3))
        estado = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert estado.deuda == d("0.00")
        assert estado.credito_a_favor_aplicable == d("3000.00")
        assert movimientos_saldo_inicial(s, cuenta) == [(d("3000.00"), MIGRACION)]


def test_c08_deuda_y_credito_en_la_misma_unidad(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Deuda y crédito en la misma unidad"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [unidad(u(mundo, 4), deuda(40, SEP, dia(9, 10), "10000.00"), credito(41, "3000.00"))],
        )
        estado = lecturas.estado_de_cuenta(s, cuenta_id=cuenta_de(s, u(mundo, 4)))
        assert estado.deuda == d("7000.00")
        assert estado.credito_a_favor == d("0.00")


def test_c08_credito_mayor_que_la_deuda(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [unidad(u(mundo, 7), deuda(70, SEP, dia(9, 10), "10000.00"), credito(71, "15000.00"))],
        )
        estado = lecturas.estado_de_cuenta(s, cuenta_id=cuenta_de(s, u(mundo, 7)))
        assert estado.deuda == d("0.00")
        assert estado.credito_a_favor == d("5000.00")


# --- C09 · Origen -----------------------------------------------------------------------------


def test_c09_origen_del_importador(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Origen del importador"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_periodos_de_u1(mundo)])
        (carga,) = cargas(s)
        assert (carga.origen, carga.archivo, carga.motivo) == ("importador", ARCHIVO, None)
        cuenta = cuenta_de(s, u(mundo, 1))
        agosto = obligacion_del(s, cuenta, AGO)
        assert filas_de(origenes(s, cuenta), obligacion=agosto.id) == {7}


def test_c09_origen_de_dos_conceptos_del_mismo_periodo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Origen de dos conceptos del mismo período"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [dos_conceptos_de_u5(mundo)])
        cuenta = cuenta_de(s, u(mundo, 5))
        o = obligacion_del(s, cuenta, SEP)
        orig = origenes(s, cuenta)
        assert filas_de(orig, obligacion=o.id) == {12, 13}
        assert filas_de(orig, movimiento=importado(s, o.id).id) == {12}


def test_c09_carga_manual_con_motivo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    motivo = "Saldos del cuaderno del administrador anterior"
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [unidad(u(mundo, 1), deuda(None, SEP, dia(9, 10), "85000.00"))],
            origen=manual(motivo),
        )
        (carga,) = cargas(s)
        assert (carga.origen, carga.archivo, carga.motivo) == ("manual", None, motivo)
        cuenta = cuenta_de(s, u(mundo, 1))
        o = obligacion_del(s, cuenta, SEP)
        assert filas_de(origenes(s, cuenta), obligacion=o.id) == {None}


# --- C10 · Replay -----------------------------------------------------------------------------


def _foto_del_resultado(r: object) -> tuple[object, ...]:
    return (
        leer(r, "operacion_id"),
        dict(leer(r, "cuentas")),
        {k: totales(v) for k, v in dict(leer(r, "por_unidad")).items()},
        totales(leer(r, "total")),
    )


def test_c10_replay_de_la_carga(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Replay de la carga"""
    op = uuid4()
    pedido = [dos_periodos_de_u1(mundo), dos_conceptos_de_u5(mundo)]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = cargar(s, mundo, pedido, operacion_id=op)
        antes = conteos(s)
        s.commit()
    poner_estado(base_del_edificio, mundo, "confirmada")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        segunda = cargar(s, mundo, pedido, operacion_id=op, confirmar=False)
        assert conteos(s) == antes, "el replay escribió"
        assert _foto_del_resultado(segunda) == _foto_del_resultado(primera)
        assert len(cargas(s)) == 1


def test_c10_replay_inmediato(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    op = uuid4()
    pedido = [dos_periodos_de_u1(mundo)]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = cargar(s, mundo, pedido, operacion_id=op)
        antes = conteos(s)
        segunda = cargar(s, mundo, pedido, operacion_id=op, confirmar=False)
        assert conteos(s) == antes, "el replay escribió"
        assert _foto_del_resultado(segunda) == _foto_del_resultado(primera)


def test_c10_mismo_pedido_en_otro_orden(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Mismo pedido en otro orden"""
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = cargar(
            s, mundo, [dos_periodos_de_u1(mundo), dos_conceptos_de_u5(mundo)], operacion_id=op
        )
        antes = conteos(s)
        al_reves = [
            unidad(
                u(mundo, 5),
                deuda(13, SEP, dia(9, 10), "20000", componente="extraordinaria"),
                deuda(12, SEP, dia(9, 10), "85000", interes="3000"),
            ),
            unidad(
                u(mundo, 1),
                deuda(8, SEP, dia(9, 10), "85000"),
                deuda(7, AGO, dia(8, 10), "80000"),
            ),
        ]
        segunda = cargar(s, mundo, al_reves, operacion_id=op, confirmar=False)
        assert conteos(s) == antes, "el mismo pedido en otro orden escribió"
        assert _foto_del_resultado(segunda) == _foto_del_resultado(primera)


# --- C11 · Lo que devuelve --------------------------------------------------------------------


def test_c11_devuelve_cuentas_y_totales(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    op = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = cargar(
            s,
            mundo,
            [
                dos_periodos_de_u1(mundo, interes_agosto="4000.00"),
                unidad(u(mundo, 4), deuda(40, SEP, dia(9, 10), "10000.00"), credito(41, "3000.00")),
            ],
            operacion_id=op,
        )
        assert leer(r, "operacion_id") == op
        cuentas = dict(leer(r, "cuentas"))
        assert cuentas == {
            u(mundo, 1): cuenta_de(s, u(mundo, 1)),
            u(mundo, 4): cuenta_de(s, u(mundo, 4)),
        }
        por_unidad = {k: totales(v) for k, v in dict(leer(r, "por_unidad")).items()}
        assert por_unidad == {
            u(mundo, 1): (d("165000.00"), d("4000.00"), d("0.00")),
            u(mundo, 4): (d("10000.00"), d("0.00"), d("3000.00")),
        }
        assert totales(leer(r, "total")) == (d("175000.00"), d("4000.00"), d("3000.00"))
        (carga,) = cargas(s)
        assert leer(r, "carga_id") == carga.id
