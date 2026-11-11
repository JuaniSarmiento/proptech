"""H-004 · C07, C08 y C13: re-emisión, huecos, días con tasa 0, replay y emisiones anuladas."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from proptech_core.cuenta_corriente.aplicacion import lecturas

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h004 import (
    DIC,
    NOV,
    OCT,
    SEP,
    anular,
    configurar,
    conteos,
    contra_asentar,
    d,
    dia,
    emitir,
    fechas,
    interes_unico,
    intereses,
    intereses_informados,
    obl,
    obligacion_de,
    pagar,
    relleno,
    sin_interes,
    tramos,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def septiembre(s: Session, mundo: Mundo) -> tuple[UUID, UUID]:
    r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
    cuenta = r.cuentas[mundo.unidades[0]]
    return cuenta, obligacion_de(s, cuenta, r.emision_id)


def anular_y_reemitir_octubre(s: Session, mundo: Mundo, o: UUID) -> UUID:
    """Emite octubre, lo anula y lo emite de nuevo; devuelve el id del interés anulado."""
    obls = [obl(mundo, 0, dia(10, 10), "50000.00")]
    primera = emitir(s, mundo, OCT, obls)
    anulado = interes_unico(s, o, dia(9, 30))
    assert anulado.importe == d("2000.00") and anulado.emision_id == primera.emision_id
    anular(s, mundo, primera.emision_id)
    emitir(s, mundo, OCT, obls)
    return anulado.id


# --- C07 · Re-emisión y huecos ---------------------------------------------------------------


def test_c07_c13_anular_y_volver_a_emitir_no_cobra_dos_veces(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Anular y volver a emitir no cobra dos veces"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        anulado = anular_y_reemitir_octubre(s, mundo, o)
        del_corte = [i for i in intereses(s, obligacion=o) if i.corte == dia(9, 30)]
        assert [i.id for i in del_corte] == [anulado], "el corte ocupado recibió otro interés"
        assert anulado not in lecturas.foto(s, cuenta).estado.movimientos_que_cuentan
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("150000.00")


def test_c07_el_corte_siguiente_recupera_el_tramo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: El corte siguiente recupera el tramo"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        anular_y_reemitir_octubre(s, mundo, o)
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("5100.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 11), dia(10, 31))]
        assert sum(t.dias for t in ts) == 51


def test_c07_el_tramo_recuperado_usa_la_tasa_del_corte_siguiente(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: El tramo recuperado usa la tasa del corte siguiente"""
    configurar(base_del_edificio, mundo, tasa="3.00")
    configurar(base_del_edificio, mundo, desde=dia(10, 1), tasa="6.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        anular_y_reemitir_octubre(s, mundo, o)
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("10200.00"), "51 días al 6%, no $2.000,00 + $6.200,00"
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 11), dia(10, 31))]
        assert {t.tasa_mensual for t in ts} == {"6.00"}


def test_c07_un_hueco_anterior_se_recupera(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Un hueco anterior se recupera aunque haya un interés posterior"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        octubre = interes_unico(s, o, dia(9, 30))
        assert octubre.importe == d("2000.00")
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        noviembre = interes_unico(s, o, dia(10, 31))
        assert noviembre.importe == d("3100.00")
        contra_asentar(s, mundo, octubre.id)
        emitir(s, mundo, DIC, relleno(mundo, DIC))
        diciembre = interes_unico(s, o, dia(11, 30))
        assert diciembre.importe == d("5000.00")
        assert fechas(tramos(s, diciembre.id)) == [
            (dia(9, 11), dia(9, 30)),
            (dia(11, 1), dia(11, 30)),
        ]
        cuentan = lecturas.foto(s, cuenta).estado.movimientos_que_cuentan
        assert noviembre.id in cuentan and octubre.id not in cuentan


def test_c07_los_dias_con_tasa_cero_se_cobran_despues(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Los días de un corte con tasa cero se cobran después"""
    configurar(base_del_edificio, mundo, tasa="0.00")
    configurar(base_del_edificio, mundo, desde=dia(10, 1), tasa="3.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o = septiembre(s, mundo)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        i = interes_unico(s, o, dia(10, 31))
        assert i.importe == d("5100.00")
        ts = tramos(s, i.id)
        assert fechas(ts) == [(dia(9, 11), dia(10, 31))]
        assert {t.tasa_mensual for t in ts} == {"3.00"}
        sin_interes(s, o, dia(9, 30))


# --- C08 · Replay ----------------------------------------------------------------------------


def test_c08_replay_inmediato_de_una_emision_con_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Replay inmediato de una emisión con interés"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        obls, eid = [obl(mundo, 0, dia(10, 10), "50000.00")], uuid4()
        emitir(s, mundo, OCT, obls, emision_id=eid)
        antes = conteos(s)
        replay = emitir(s, mundo, OCT, obls, emision_id=eid)
        assert intereses_informados(replay)[cuenta] == [(o, dia(9, 30), d("2000.00"))]
        assert replay.saldo_anterior[cuenta] == d("102000.00")
        assert conteos(s) == antes, "el replay escribió"


def test_c08_replay_despues_de_un_pago(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Replay después de un pago"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        obls, eid = [obl(mundo, 0, dia(10, 10), "50000.00")], uuid4()
        emitir(s, mundo, OCT, obls, emision_id=eid)
        pagar(s, mundo, cuenta, "30000.00", dia(10, 5))
        antes = conteos(s)
        replay = emitir(s, mundo, OCT, obls, emision_id=eid)
        assert intereses_informados(replay)[cuenta] == [(o, dia(9, 30), d("2000.00"))]
        assert replay.saldo_anterior[cuenta] == d("72000.00")
        assert conteos(s) == antes, "el replay escribió"


def test_c08_replay_despues_de_anular(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Replay después de anular"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta, o = septiembre(s, mundo)
        obls, eid = [obl(mundo, 0, dia(10, 10), "50000.00")], uuid4()
        emitir(s, mundo, OCT, obls, emision_id=eid)
        anular(s, mundo, eid)
        antes = conteos(s)
        replay = emitir(s, mundo, OCT, obls, emision_id=eid)
        assert intereses_informados(replay)[cuenta] == [(o, dia(9, 30), d("2000.00"))], (
            "el replay devuelve también el interés que ya no cuenta"
        )
        assert replay.saldo_anterior[cuenta] == d("100000.00")
        assert conteos(s) == antes, "el replay escribió"


# --- C13 · Emisión anulada -------------------------------------------------------------------


def test_c13_emision_anulada_no_genera_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Emisión anulada no genera interés sobre sus obligaciones"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
        c0 = primera.cuentas[mundo.unidades[0]]
        o0 = obligacion_de(s, c0, primera.emision_id)
        anular(s, mundo, primera.emision_id)
        segunda = emitir(s, mundo, SEP, [obl(mundo, 1, dia(9, 10))])
        c1 = segunda.cuentas[mundo.unidades[1]]
        o1 = obligacion_de(s, c1, segunda.emision_id)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o1, dia(9, 30)).importe == d("2000.00"), "control: la vigente sí"
        sin_interes(s, o0)
