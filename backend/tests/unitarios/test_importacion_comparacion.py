"""Tarea 2.3 de `importacion-desde-excel`: la comparación pura del borrador contra el control
(design D6, E13). Sin base: recibe las filas ya guardadas. El saldo del borrador de una unidad es
capital más interés importado menos crédito; la diferencia es borrador menos control y se mira por
unidad (un total igual no oculta dos errores de signo opuesto). Datos inventados."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.importacion.dominio.comparacion import (
    SaldoGuardado,
    aviso_de_mes_entero,
    comparar_saldos,
)

U1A, U1B, U2A, U2B, U3C = (uuid4() for _ in range(5))
NOMBRES = {U1A: "1A", U1B: "1B", U2A: "2A", U2B: "2B", U3C: "3C"}


def _d(texto: str) -> Dinero:
    return Dinero(texto)


def _fila(unidad: UUID, tipo: str, importe: str, interes: str = "0.00") -> SaldoGuardado:
    return SaldoGuardado(unidad, tipo, _d(importe), _d(interes))


def _por_nombre(comparacion: object) -> dict[str, tuple[str, str, str]]:
    return {
        u.unidad: (u.borrador.a_texto(), u.control.a_texto(), u.diferencia.a_texto())
        for u in comparacion.unidades  # type: ignore[attr-defined]
    }


def test_borrador_es_capital_mas_interes_menos_credito() -> None:
    filas = [
        _fila(U1A, "detalle", "80000.00", "4000.00"),
        _fila(U1A, "detalle", "85000.00"),
        _fila(U1A, "credito", "1000.00"),
    ]
    c = comparar_saldos(NOMBRES, filas, {U1A: _d("168000.00")})
    assert _por_nombre(c) == {"1A": ("168000.00", "168000.00", "0.00")}


def test_el_credito_resta_y_el_total_suma() -> None:
    filas = [_fila(U2A, "total", "50000.00", "2000.00"), _fila(U2B, "credito", "3000.00")]
    c = comparar_saldos(NOMBRES, filas, {U2A: _d("52000.00"), U2B: _d("-3000.00")})
    assert _por_nombre(c) == {
        "2A": ("52000.00", "52000.00", "0.00"),
        "2B": ("-3000.00", "-3000.00", "0.00"),
    }


def test_dos_errores_de_signo_opuesto_coinciden_en_el_total_pero_no_por_unidad() -> None:
    filas = [_fila(U1A, "total", "169000.00"), _fila(U2A, "total", "52000.00")]
    c = comparar_saldos(NOMBRES, filas, {U1A: _d("159000.00"), U2A: _d("62000.00")})
    assert (c.total_borrador.a_texto(), c.total_control.a_texto()) == ("221000.00", "221000.00")
    assert _por_nombre(c) == {
        "1A": ("169000.00", "159000.00", "10000.00"),
        "2A": ("52000.00", "62000.00", "-10000.00"),
    }
    assert c.unidades_con_diferencia == 2


def test_una_unidad_con_control_y_sin_saldo_y_al_reves() -> None:
    filas = [_fila(U1B, "total", "1000.00")]
    c = comparar_saldos(NOMBRES, filas, {U3C: _d("5000.00")})
    assert _por_nombre(c) == {
        "1B": ("1000.00", "0.00", "1000.00"),
        "3C": ("0.00", "5000.00", "-5000.00"),
    }
    assert c.unidades_con_diferencia == 2


def test_un_credito_igual_a_su_control_no_tiene_diferencia() -> None:
    c = comparar_saldos(NOMBRES, [_fila(U2B, "credito", "3000.00")], {U2B: _d("-3000.00")})
    assert _por_nombre(c) == {"2B": ("-3000.00", "-3000.00", "0.00")}
    assert c.unidades_con_diferencia == 0


def test_totales_y_cantidad_de_diferencias() -> None:
    filas = [_fila(U1A, "total", "100.00"), _fila(U1B, "total", "200.00")]
    c = comparar_saldos(NOMBRES, filas, {U1A: _d("100.00"), U1B: _d("150.50")})
    assert (c.total_borrador.a_texto(), c.total_control.a_texto()) == ("300.00", "250.50")
    assert c.unidades_con_diferencia == 1


def test_las_unidades_salen_ordenadas_por_identificador_y_sin_las_que_no_figuran() -> None:
    filas = [_fila(U2A, "total", "1.00"), _fila(U1A, "total", "1.00")]
    c = comparar_saldos(NOMBRES, filas, {U3C: _d("1.00")})
    assert [u.unidad for u in c.unidades] == ["1A", "2A", "3C"]
    assert all(u.unidad_id in NOMBRES for u in c.unidades)


def test_con_deuda_es_capital_mayor_que_cero_no_interes_ni_credito() -> None:
    filas = [
        _fila(U1A, "detalle", "80000.00"),
        _fila(U1B, "total", "0.00", "10.00"),  # no llega por la validación, pero el dominio no cree
        _fila(U2B, "credito", "3000.00"),
    ]
    c = comparar_saldos(NOMBRES, filas, {})
    con_deuda = {u.unidad: u.con_deuda for u in c.unidades}
    assert con_deuda == {"1A": True, "1B": False, "2B": False}


def test_una_unidad_con_solo_control_no_tiene_deuda() -> None:
    c = comparar_saldos(NOMBRES, [], {U3C: _d("5000.00")})
    assert [u.con_deuda for u in c.unidades] == [False]


def test_sin_filas_ni_control_la_comparacion_esta_vacia() -> None:
    c = comparar_saldos(NOMBRES, [], {})
    assert c.unidades == ()
    assert (c.total_borrador.a_texto(), c.total_control.a_texto()) == ("0.00", "0.00")
    assert c.unidades_con_diferencia == 0


@pytest.mark.parametrize(
    ("migracion", "texto"),
    [
        (date(2026, 10, 15), "El primer interés del sistema cubre octubre de 2026"),
        (date(2026, 1, 1), "El primer interés del sistema cubre enero de 2026"),
        (date(2027, 3, 31), "El primer interés del sistema cubre marzo de 2027"),
        (date(2026, 9, 30), "El primer interés del sistema cubre septiembre de 2026"),
        (date(2026, 12, 2), "El primer interés del sistema cubre diciembre de 2026"),
    ],
)
def test_el_aviso_nombra_el_mes_de_la_migracion_en_minuscula(migracion: date, texto: str) -> None:
    assert aviso_de_mes_entero(migracion) == texto


def test_los_doce_meses_tienen_su_nombre() -> None:
    meses = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    assert [aviso_de_mes_entero(date(2026, m, 1)) for m in range(1, 13)] == [
        f"El primer interés del sistema cubre {mes} de 2026" for mes in meses
    ]
