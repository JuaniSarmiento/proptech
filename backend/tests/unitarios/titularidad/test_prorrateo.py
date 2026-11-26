"""El prorrateo por días de la expensa del mes del cambio (H-032, R32, D-168.5). Sin base."""

from datetime import date
from uuid import uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.titularidad.dominio.cambio import CambioInvalido, validar_vendedor_deudor
from proptech_core.titularidad.dominio.prorrateo import (
    dias_del_mes,
    dias_del_vendedor,
    parte_a_trasladar,
    parte_por_dias,
)


def test_los_dias_del_vendedor_son_los_anteriores_a_la_fecha() -> None:
    assert dias_del_vendedor(date(2026, 11, 11)) == 10
    assert dias_del_vendedor(date(2026, 11, 1)) == 0
    assert dias_del_vendedor(date(2026, 11, 30)) == 29


def test_los_dias_del_mes_son_los_del_calendario() -> None:
    assert dias_del_mes(date(2026, 11, 11)) == 30
    assert dias_del_mes(date(2026, 12, 1)) == 31
    assert dias_del_mes(date(2028, 2, 11)) == 29
    assert dias_del_mes(date(2027, 2, 11)) == 28


@pytest.mark.parametrize(
    ("componente", "dias", "del_mes", "esperada"),
    [
        ("30000.31", 15, 30, "15000.16"),  # 15000.155: medio centavo hacia arriba
        ("1500.02", 15, 30, "750.01"),
        ("15000.01", 15, 30, "7500.01"),  # 7500.005
        ("100.00", 10, 30, "33.33"),
        ("100.00", 20, 30, "66.67"),
        ("100.00", 0, 30, "0.00"),
        ("100.00", 29, 30, "96.67"),
        ("0.00", 10, 30, "0.00"),
        ("0.01", 15, 30, "0.01"),  # 0.005 sube
        ("0.01", 14, 30, "0.00"),
    ],
)
def test_parte_por_dias_redondea_medio_hacia_arriba(
    componente: str, dias: int, del_mes: int, esperada: str
) -> None:
    assert parte_por_dias(Dinero(componente), dias, del_mes) == Dinero(esperada)


def test_el_vendedor_y_la_unidad_suman_exacto() -> None:
    total = Dinero("30000.31")
    parte = parte_por_dias(total, 15, 30)
    assert parte + (total - parte) == total


@pytest.mark.parametrize(
    ("emitido", "impago", "esperada"),
    [
        ("30000.31", "30000.31", "15000.16"),  # nada pagado
        ("30000.31", "25000.31", "10000.16"),  # pagado 5000: baja la parte del vendedor
        ("30000.31", "10000.00", "0.00"),  # pagado 20000.31 > parte: max(., 0)
        ("30000.31", "0.00", "0.00"),
    ],
)
def test_lo_ya_pagado_se_descuenta_de_la_parte_del_vendedor(
    emitido: str, impago: str, esperada: str
) -> None:
    assert parte_a_trasladar(Dinero(emitido), Dinero(impago), 15, 30) == Dinero(esperada)


def test_con_prorrateo_el_deudor_se_nombra_igual_que_con_la_deuda_a_nombre_del_vendedor() -> None:
    a, b = uuid4(), uuid4()
    assert (
        validar_vendedor_deudor(
            deuda_previa="en_la_unidad", vendedor_deudor=None, vendedores=[a], con_prorrateo=True
        )
        == a
    )
    assert (
        validar_vendedor_deudor(
            deuda_previa="en_la_unidad", vendedor_deudor=b, vendedores=[a, b], con_prorrateo=True
        )
        == b
    )
    with pytest.raises(CambioInvalido) as error:
        validar_vendedor_deudor(
            deuda_previa="en_la_unidad", vendedor_deudor=None, vendedores=[a, b], con_prorrateo=True
        )
    assert error.value.campo == "vendedor_deudor"
    with pytest.raises(CambioInvalido):
        validar_vendedor_deudor(
            deuda_previa="en_la_unidad", vendedor_deudor=uuid4(), vendedores=[a], con_prorrateo=True
        )


def test_sin_prorrateo_ni_deuda_a_su_nombre_no_hay_deudor() -> None:
    a = uuid4()
    assert (
        validar_vendedor_deudor(deuda_previa="en_la_unidad", vendedor_deudor=None, vendedores=[a])
        is None
    )
    with pytest.raises(CambioInvalido):
        validar_vendedor_deudor(
            deuda_previa="en_la_unidad", vendedor_deudor=a, vendedores=[a], con_prorrateo=False
        )
