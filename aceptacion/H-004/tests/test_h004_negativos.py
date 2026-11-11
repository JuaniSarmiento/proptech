"""H-004 · C10, C11, C12 y C23 a C27: lo que tiene que rechazarse o no registrar nada.

Cada "no registra" lleva un control en la misma corrida que sí registra: así el test no pasa
porque no se calcula ningún interés, sino porque ese caso no lo genera.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto, NoEncontrado

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h004 import (
    NOV,
    OCT,
    SEP,
    configurar,
    conteos,
    d,
    dia,
    emitir,
    interes_unico,
    intereses,
    obl,
    obligacion_de,
    pagar,
    relleno,
    sin_interes,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def septiembre_de_dos(
    s: Session, mundo: Mundo, vencimiento_0: object, ordinaria_0: str = "100000.00"
) -> tuple[UUID, UUID, UUID, UUID]:
    """Septiembre con la unidad 0 (el caso) y la 1 (el control, $100.000 vencida el 10/09)."""
    r = emitir(
        s,
        mundo,
        SEP,
        [obl(mundo, 0, vencimiento_0, ordinaria_0), obl(mundo, 1, dia(9, 10))],  # type: ignore[arg-type]
    )
    c0, c1 = (r.cuentas[mundo.unidades[n]] for n in (0, 1))
    return c0, obligacion_de(s, c0, r.emision_id), c1, obligacion_de(s, c1, r.emision_id)


def control(s: Session, o1: UUID) -> None:
    assert interes_unico(s, o1, dia(9, 30)).importe == d("2000.00"), "control: la impaga sí"


# --- C10 · Tasa 0 o importe que redondea a cero ----------------------------------------------


def test_c10_tasa_cero(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Tasa cero"""
    configurar(base_del_edificio, mundo, tasa="0.00")
    configurar(base_del_edificio, mundo, complejo=mundo.otro_complejo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
        o = obligacion_de(s, r.cuentas[mundo.unidades[0]], r.emision_id)
        otra = ObligacionAEmitir(
            mundo.unidad_otro_complejo, dia(9, 10), d("100000.00"), d("0.00"), d("0.00")
        )
        r2 = emitir(s, mundo, SEP, [otra], complejo=mundo.otro_complejo)
        o2 = obligacion_de(s, r2.cuentas[mundo.unidad_otro_complejo], r2.emision_id)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        emitir(
            s,
            mundo,
            OCT,
            [
                ObligacionAEmitir(
                    mundo.unidad_otro_complejo, dia(10, 10), d("1.00"), d("0.00"), d("0.00")
                )
            ],
            complejo=mundo.otro_complejo,
        )
        assert interes_unico(s, o2, dia(9, 30)).importe == d("2000.00"), "control: al 3% sí"
        sin_interes(s, o)


def test_c10_importe_que_redondea_a_cero(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o0, _, o1 = septiembre_de_dos(s, mundo, dia(9, 29), "0.10")
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        control(s, o1)
        sin_interes(s, o0)


# --- C11 · Sin configuración vigente al corte -------------------------------------------------


def _rechazo_por_configuracion(s: Session, mundo: Mundo) -> None:
    emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
    antes = conteos(s)
    with pytest.raises(Conflicto) as e:
        emitir(s, mundo, OCT, relleno(mundo, OCT))
    assert e.value.campo == "configuracion"
    assert conteos(s) == antes, "el libro cambió"


def test_c11_sin_configuracion_vigente(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Sin configuración vigente"""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _rechazo_por_configuracion(s, mundo)


def test_c11_solo_una_version_futura(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Sólo una versión futura"""
    configurar(base_del_edificio, mundo, desde=dia(10, 1))
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _rechazo_por_configuracion(s, mundo)


# --- C12 · Edificio de otra administración ---------------------------------------------------


def test_c12_edificio_de_otra_administracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Edificio de otra administración"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
        s.commit()
        antes = conteos(s)
    with sesion_app(base_del_edificio, mundo.admin_b) as b:
        with pytest.raises(NoEncontrado):
            emitir(b, mundo, OCT, [obl(mundo, 0, dia(10, 10))], identidad=mundo.identidad_b)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert conteos(s) == antes, "el libro cambió"


# --- C23 a C27 · Bordes que no generan interés -----------------------------------------------


def test_c23_vence_el_dia_del_corte(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o0, _, o1 = septiembre_de_dos(s, mundo, dia(9, 30))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        control(s, o1)
        sin_interes(s, o0, dia(9, 30))


def test_c24_vence_despues_del_corte(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, o0, _, o1 = septiembre_de_dos(s, mundo, dia(10, 5))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        control(s, o1)
        sin_interes(s, o0, dia(9, 30))


def test_c25_pagada_entera_el_dia_del_vencimiento(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        c0, o0, _, o1 = septiembre_de_dos(s, mundo, dia(9, 10))
        pagar(s, mundo, c0, "100000.00", dia(9, 10))
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        control(s, o1)
        emitir(s, mundo, NOV, relleno(mundo, NOV))
        sin_interes(s, o0)


def test_c26_otro_edificio_de_la_misma_administracion(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    configurar(base_del_edificio, mundo, complejo=mundo.otro_complejo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
        o = obligacion_de(s, r.cuentas[mundo.unidades[0]], r.emision_id)
        otra = ObligacionAEmitir(
            mundo.unidad_otro_complejo, dia(9, 10), d("100000.00"), d("0.00"), d("0.00")
        )
        r2 = emitir(s, mundo, SEP, [otra], complejo=mundo.otro_complejo)
        cuenta_b = r2.cuentas[mundo.unidad_otro_complejo]
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("2000.00"), "control: el edificio A sí"
        assert intereses(s, cuenta=cuenta_b) == [], "la emisión del A tocó una cuenta del B"


def test_c27_las_cuentas_de_persona_no_reciben_interes(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta_persona, ahora = uuid4(), datetime(2026, 9, 1, 12, tzinfo=UTC)
        s.execute(
            text(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, persona_id, creada_en) "
                "VALUES (:id, :adm, :c, :p, :en)"
            ),
            {
                "id": cuenta_persona,
                "adm": mundo.admin,
                "c": mundo.complejo,
                "p": mundo.persona,
                "en": ahora,
            },
        )
        s.execute(
            text(
                "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, "
                "operacion_id, periodo, vencimiento, ordinaria, fondo_de_reserva, "
                "extraordinaria, registrada_en) "
                "VALUES (:id, :adm, :c, :cuenta, :op, :p, :v, '100000.00', '0.00', '0.00', :en)"
            ),
            {
                "id": uuid4(),
                "adm": mundo.admin,
                "c": mundo.complejo,
                "cuenta": cuenta_persona,
                "op": uuid4(),
                "p": SEP,
                "v": dia(9, 10),
                "en": ahora,
            },
        )
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10))])
        o = obligacion_de(s, r.cuentas[mundo.unidades[0]], r.emision_id)
        emitir(s, mundo, OCT, relleno(mundo, OCT))
        assert interes_unico(s, o, dia(9, 30)).importe == d("2000.00"), "control: la unidad sí"
        assert intereses(s, cuenta=cuenta_persona) == [], "una cuenta de persona recibió interés"
