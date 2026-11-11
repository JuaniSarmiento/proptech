"""H-006 · C01 a C10, C12 y C13: cuánto hay vencido, el umbral de saldos chicos, la deuda de
intereses y el moroso crítico, derivados del libro a una fecha (spec `situacion-de-cobranza`,
design D6, elecciones E6, E7, E8 y E14 firmadas por Juani el 11/11/2026).

Cada test arma su configuración y su deuda con los casos de uso reales del libro; salvo que diga
otra cosa: umbral $500, gracia 0 y tasa 0."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir

from .._cuenta_corriente import Mundo, sembrar, sesion_app
from .._edificios import BaseDeEdificio
from ._h006 import (
    AGO,
    OCT,
    SEP,
    anular,
    bajo_umbral,
    cargar,
    configurar,
    contra_asentar,
    cuenta_de,
    cuentas_de_unidad,
    d,
    de_cuenta,
    del_edificio,
    deuda,
    deuda_de_intereses,
    dia,
    emitir,
    etiqueta,
    intereses_de_la_cuenta,
    leer,
    liquidaciones,
    moroso,
    obl,
    pagar,
    situacion,
    solo_interes,
    total,
    total_vencido,
    unidad,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def dos_periodos(s: Session, mundo: Mundo, n: int, agosto: str, septiembre: str) -> UUID:
    """Agosto (vence 10/08) y septiembre (vence 10/09) de la unidad `n`, emitidos e impagos."""
    r = emitir(s, mundo, AGO, [obl(mundo, n, dia(8, 10), agosto)])
    emitir(s, mundo, SEP, [obl(mundo, n, dia(9, 10), septiembre)])
    return r.cuentas[mundo.unidades[n]]


def solo_septiembre(s: Session, mundo: Mundo, n: int, importe: str) -> UUID:
    r = emitir(s, mundo, SEP, [obl(mundo, n, dia(9, 10), importe)])
    return r.cuentas[mundo.unidades[n]]


# --- C01 · Vencida desde que corre el interés -------------------------------------------------


def test_c01_dentro_de_la_gracia(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Dentro de la gracia"""
    configurar(base_del_edificio, mundo, gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = solo_septiembre(s, mundo, 0, "100000.00")
        al_15 = de_cuenta(s, cuenta, dia(9, 15))
        assert (total_vencido(al_15), liquidaciones(al_15)) == (d("0.00"), 0), (
            "al 15/09 (dentro de la gracia) no está vencida"
        )
        assert etiqueta(al_15) == "sin_deuda_vencida"
        al_16 = de_cuenta(s, cuenta, dia(9, 16))
        assert (total_vencido(al_16), liquidaciones(al_16)) == (d("100000.00"), 1), (
            "al 16/09 ya está vencida"
        )


# --- C02 · Total vencido con el interés en su período ------------------------------------------


def test_c02_interes_en_su_periodo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Interés en su período"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                unidad(
                    mundo.unidades[1],
                    deuda(7, AGO, dia(8, 10), "80000.00", interes="4000.00"),
                    deuda(8, SEP, dia(9, 10), "85000.00"),
                )
            ],
        )
        sit = de_cuenta(s, cuenta_de(s, mundo.unidades[1]), dia(10, 31))
        assert total_vencido(sit) == d("169000.00")
        assert liquidaciones(sit) == 2, (
            "el interés cuenta en su período: dos liquidaciones, no tres"
        )


# --- C03 · Umbral de saldos chicos ------------------------------------------------------------


def test_c03_saldo_chico(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Saldo chico"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 2, "150.00", "150.00")
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert total_vencido(sit) == d("300.00")
        assert bajo_umbral(sit) and not moroso(sit) and not deuda_de_intereses(sit)
        assert etiqueta(sit) == "bajo_umbral"


def test_c03_dos_saldos_chicos_que_juntos_pasan_el_umbral(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Dos saldos chicos que juntos pasan el umbral"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 2, "300.00", "250.00")
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert total_vencido(sit) == d("550.00")
        assert not bajo_umbral(sit) and moroso(sit)


def test_c03_justo_en_el_umbral(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Justo en el umbral"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 2, "250.00", "250.00")
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert total_vencido(sit) == d("500.00")
        assert not bajo_umbral(sit), "$500 o más no queda bajo el umbral (D-143, E6)"
        assert moroso(sit)


def test_c03_el_umbral_no_frena_el_interes(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: El umbral no frena el interés"""
    configurar(base_del_edificio, mundo, tasa="3.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = solo_septiembre(s, mundo, 3, "300.00")
        assert bajo_umbral(de_cuenta(s, cuenta, dia(9, 30))), (
            "control: la cuenta está bajo el umbral"
        )
        emitir(s, mundo, OCT, [obl(mundo, 4, dia(10, 10), "1.00")])
        assert intereses_de_la_cuenta(s, cuenta) == [d("6.00")], (
            "la emisión de octubre registra el interés de los $300 (20 días al 3%)"
        )


# --- C04 · Moroso crítico ---------------------------------------------------------------------


def test_c04_una_sola_vencida(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Una sola vencida"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = solo_septiembre(s, mundo, 0, "85000.00")
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert (liquidaciones(sit), moroso(sit)) == (1, False)
        assert etiqueta(sit) == "con_deuda_vencida"


def test_c04_dos_vencidas_con_saldo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Dos vencidas con saldo"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "80000.00", "85000.00")
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert (total_vencido(sit), liquidaciones(sit), moroso(sit)) == (d("165000.00"), 2, True)
        assert etiqueta(sit) == "moroso_critico"


def test_c04_pago_parcial_que_no_cancela_ninguna(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Pago parcial que no cancela ninguna"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "80000.00", "85000.00")
        pagar(s, mundo, cuenta, "30000.00", dia(9, 20))
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert (total_vencido(sit), liquidaciones(sit), moroso(sit)) == (d("135000.00"), 2, True)


def test_c04_un_saldo_grande_y_uno_chico(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Un saldo grande y uno chico"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "500.00", "20.00")
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert (total_vencido(sit), bajo_umbral(sit), moroso(sit)) == (d("520.00"), False, True)


def test_c04_un_periodo_con_solo_interes_no_cuenta(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Un período con sólo interés no cuenta"""
    configurar(base_del_edificio, mundo, tasa="10.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, AGO, [obl(mundo, 4, dia(8, 10), "80000.00")])
        cuenta = r.cuentas[mundo.unidades[4]]
        pagar(s, mundo, cuenta, "80000.00", dia(8, 25))
        emitir(s, mundo, SEP, [obl(mundo, 4, dia(9, 10), "85000.00")])
        assert intereses_de_la_cuenta(s, cuenta) == [d("4000.00")], (
            "control: agosto queda con sólo $4.000 de interés impago"
        )
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert total_vencido(sit) == d("89000.00")
        assert liquidaciones(sit) == 1, "agosto con sólo interés no cuenta como liquidación (E7)"
        assert not moroso(sit) and not deuda_de_intereses(sit)
        assert etiqueta(sit) == "con_deuda_vencida"


def test_c04_deshacer_un_pago_vuelve_a_marcar(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Deshacer un pago vuelve a marcar"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "80000.00", "85000.00")
        pago = pagar(s, mundo, cuenta, "80000.00", dia(9, 20))
        antes = de_cuenta(s, cuenta, dia(9, 30))
        assert (liquidaciones(antes), moroso(antes)) == (1, False), "control: agosto pagado"
        contra_asentar(s, mundo, pago)
        despues = de_cuenta(s, cuenta, dia(9, 30))
        assert (liquidaciones(despues), moroso(despues)) == (2, True)


# --- C05 · Deuda de intereses -----------------------------------------------------------------


def test_c05_solo_intereses(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Sólo intereses"""
    configurar(base_del_edificio, mundo, tasa="10.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = solo_interes(s, mundo, 5, "80000.00")
        emitir(s, mundo, SEP, [obl(mundo, 6, dia(9, 10), "1.00")])
        assert intereses_de_la_cuenta(s, cuenta) == [d("4000.00")], "control: $4.000 de interés"
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert total_vencido(sit) == d("4000.00")
        assert deuda_de_intereses(sit) and not moroso(sit) and not bajo_umbral(sit)
        assert liquidaciones(sit) == 0
        assert etiqueta(sit) == "deuda_de_intereses"


# --- C06 · Saldo inicial ----------------------------------------------------------------------


def test_c06_migrada_con_dos_periodos(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Migrada con dos períodos"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(
            s,
            mundo,
            [
                unidad(
                    mundo.unidades[1],
                    deuda(7, AGO, dia(8, 10), "80000.00"),
                    deuda(8, SEP, dia(9, 10), "85000.00"),
                )
            ],
        )
        sit = de_cuenta(s, cuenta_de(s, mundo.unidades[1]), dia(10, 31))
        assert (liquidaciones(sit), moroso(sit)) == (2, True)


def test_c06_migrada_con_total_unico(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Migrada con total único"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cargar(s, mundo, [unidad(mundo.unidades[2], total(9, "50000.00"), modo="total")])
        sit = de_cuenta(s, cuenta_de(s, mundo.unidades[2]), dia(10, 31))
        assert (total_vencido(sit), liquidaciones(sit), moroso(sit)) == (d("50000.00"), 1, False)


# --- C07 · La fecha clasifica, no reconstruye (E14) -------------------------------------------


def test_c07_un_pago_posterior_cuenta_aunque_la_fecha_sea_anterior(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Escenario: Un pago posterior cuenta aunque la fecha sea anterior"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "80000.00", "85000.00")
        assert moroso(de_cuenta(s, cuenta, dia(9, 30))), "control: moroso antes de pagar"
        pagar(s, mundo, cuenta, "165000.00", dia(10, 20))
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert (total_vencido(sit), moroso(sit)) == (d("0.00"), False)
        assert etiqueta(sit) == "sin_deuda_vencida"


# --- C08 · Por edificio -----------------------------------------------------------------------


def test_c08_listado_del_edificio(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Listado del edificio"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(
            s,
            mundo,
            AGO,
            [obl(mundo, 0, dia(8, 10), "80000.00"), obl(mundo, 2, dia(8, 10), "150.00")],
        )
        emitir(
            s,
            mundo,
            SEP,
            [
                obl(mundo, 0, dia(9, 10), "85000.00"),
                obl(mundo, 1, dia(9, 10), "85000.00"),
                obl(mundo, 2, dia(9, 10), "150.00"),
            ],
        )
        otro = emitir(
            s,
            mundo,
            AGO,
            [
                ObligacionAEmitir(
                    mundo.unidad_otro_complejo, dia(8, 10), d("1000.00"), d("0.00"), d("0.00")
                )
            ],
            complejo=mundo.otro_complejo,
        )
        listado = del_edificio(s, mundo.complejo, dia(10, 31))
        por_cuenta = {UUID(str(leer(x, "cuenta_id"))): x for x in listado}
        assert len(por_cuenta) == len(listado), "una entrada por cuenta"
        assert set(por_cuenta) == cuentas_de_unidad(s, mundo.complejo), (
            "una entrada por cada cuenta de unidad del edificio, ninguna de otro edificio"
        )
        assert next(iter(otro.cuentas.values())) not in por_cuenta
        u0, u1, u2 = (cuenta_de(s, mundo.unidades[n]) for n in (0, 1, 2))
        for cuenta, unidad_id in ((u0, mundo.unidades[0]), (u1, mundo.unidades[1])):
            assert UUID(str(leer(por_cuenta[cuenta], "unidad_id"))) == unidad_id
        assert situacion(por_cuenta[u0]) == (
            d("165000.00"),
            2,
            False,
            False,
            True,
            "moroso_critico",
        )
        assert situacion(por_cuenta[u1]) == (
            d("85000.00"),
            1,
            False,
            False,
            False,
            "con_deuda_vencida",
        )
        assert situacion(por_cuenta[u2])[0::2] == (d("300.00"), True, False)
        assert etiqueta(por_cuenta[u2]) == "bajo_umbral"


# --- C09 · La etiqueta respeta la precedencia de D6 -------------------------------------------


ETIQUETA_ESPERADA = {
    "sin_deuda_vencida": "sin_deuda_vencida",
    "bajo_umbral_antes_que_moroso": "bajo_umbral",
    "bajo_umbral_antes_que_deuda_de_intereses": "bajo_umbral",
    "deuda_de_intereses": "deuda_de_intereses",
    "moroso_critico": "moroso_critico",
    "con_deuda_vencida": "con_deuda_vencida",
}


@pytest.mark.parametrize("caso", sorted(ETIQUETA_ESPERADA))
def test_c09_la_etiqueta_respeta_la_precedencia(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, caso: str
) -> None:
    """Una etiqueta por cuenta, con la precedencia de D6: sin deuda vencida → bajo el umbral →
    deuda de intereses → moroso crítico → con deuda vencida."""
    configurar(base_del_edificio, mundo, tasa="10.00" if "intereses" in caso else "0.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        if caso == "sin_deuda_vencida":
            cuenta, fecha = solo_septiembre(s, mundo, 0, "100000.00"), dia(9, 10)
        elif caso == "bajo_umbral_antes_que_moroso":
            cuenta, fecha = dos_periodos(s, mundo, 0, "300.00", "100.00"), dia(9, 30)
        elif caso == "bajo_umbral_antes_que_deuda_de_intereses":
            cuenta, fecha = solo_interes(s, mundo, 0, "8000.00"), dia(9, 30)
            emitir(s, mundo, SEP, [obl(mundo, 6, dia(9, 10), "1.00")])
            assert intereses_de_la_cuenta(s, cuenta) == [d("400.00")], "control: $400 de interés"
        elif caso == "deuda_de_intereses":
            cuenta, fecha = solo_interes(s, mundo, 0, "80000.00"), dia(9, 30)
            emitir(s, mundo, SEP, [obl(mundo, 6, dia(9, 10), "1.00")])
        elif caso == "moroso_critico":
            cuenta, fecha = dos_periodos(s, mundo, 0, "80000.00", "85000.00"), dia(9, 30)
        else:
            cuenta, fecha = solo_septiembre(s, mundo, 0, "85000.00"), dia(9, 30)
        sit = de_cuenta(s, cuenta, fecha)
        assert etiqueta(sit) == ETIQUETA_ESPERADA[caso]
        if caso.startswith("bajo_umbral"):
            assert not moroso(sit) and not deuda_de_intereses(sit), (
                "bajo el umbral no cuenta para R20 ni como deuda de intereses (R30)"
            )


# --- C10 · Configuración vigente a la fecha ---------------------------------------------------


def test_c10_el_umbral_es_el_de_la_version_vigente_a_la_fecha(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo, umbral="500.00")
    configurar(base_del_edificio, mundo, desde=dia(10, 1), umbral="1000.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "350.00", "350.00")
        al_30_09 = de_cuenta(s, cuenta, dia(9, 30))
        assert (bajo_umbral(al_30_09), moroso(al_30_09)) == (False, True), "con umbral $500"
        al_31_10 = de_cuenta(s, cuenta, dia(10, 31))
        assert (bajo_umbral(al_31_10), moroso(al_31_10)) == (True, False), "con umbral $1.000"


# --- C12 · Emisión anulada --------------------------------------------------------------------


def test_c12_emision_anulada(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    """Escenario: Emisión anulada"""
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, SEP, [obl(mundo, 0, dia(9, 10), "85000.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        assert liquidaciones(de_cuenta(s, cuenta, dia(9, 30))) == 1, (
            "control: vencida antes de anular"
        )
        anular(s, mundo, r.emision_id)
        sit = de_cuenta(s, cuenta, dia(9, 30))
        assert (total_vencido(sit), liquidaciones(sit)) == (d("0.00"), 0)
        assert etiqueta(sit) == "sin_deuda_vencida"


# --- C13 · Bordes de "vencida" ----------------------------------------------------------------


def test_c13_el_dia_del_fin_de_la_gracia_no_esta_vencida(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = solo_septiembre(s, mundo, 0, "85000.00")
        el_dia = de_cuenta(s, cuenta, dia(9, 10))
        assert (total_vencido(el_dia), liquidaciones(el_dia)) == (d("0.00"), 0), (
            "con gracia 0, el día del vencimiento todavía no está vencida"
        )
        assert liquidaciones(de_cuenta(s, cuenta, dia(9, 11))) == 1, "control: al día siguiente sí"


def test_c13_una_obligacion_que_vence_despues_de_la_fecha(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    configurar(base_del_edificio, mundo)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo, 0, "80000.00", "85000.00")
        sit = de_cuenta(s, cuenta, dia(9, 5))
        assert (total_vencido(sit), liquidaciones(sit)) == (d("80000.00"), 1), (
            "al 05/09 sólo agosto está vencido"
        )
