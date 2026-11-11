"""H-008 · C13 y C14: las hojas `Saldos` y `Control` mal formadas se rechazan enteras, con un
informe por fila (hoja, fila, columna, motivo) y sin escribir nada.

Fila del Excel = índice + 2 (el encabezado es la fila 1). Cada caso cambia una sola cosa de la base.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from ._h008 import (
    ENC_CONTROL,
    ENC_SALDOS,
    Mundo,
    archivo,
    conteos,
    control_base,
    errores,
    importar,
    saldos_base,
    ubicaciones,
)

pytestmark = pytest.mark.integracion

Filas = list[list[Any]]


def _cambiar(fila: int, columna: int, valor: Any) -> Callable[[Filas], Filas]:
    def cambio(filas: Filas) -> Filas:
        filas[fila - 2][columna] = valor
        return filas

    return cambio


def _agregar(*nuevas: list[Any]) -> Callable[[Filas], Filas]:
    def cambio(filas: Filas) -> Filas:
        return [*filas, *[list(n) for n in nuevas]]

    return cambio


# Columnas de `Saldos`: 0 Unidad, 1 Período, 2 Vencimiento, 3 Concepto, 4 Importe, 5 Interés.
CASOS_DE_SALDOS: dict[str, tuple[Callable[[Filas], Filas], tuple[str, int, str]]] = {
    "unidad_inexistente": (_cambiar(2, 0, "9Z"), ("Saldos", 2, "Unidad")),
    "periodo_posterior_al_mes_de_migracion": (_cambiar(3, 1, "2026-11"), ("Saldos", 3, "Período")),
    "periodo_que_no_es_un_mes": (_cambiar(3, 1, "2026-13"), ("Saldos", 3, "Período")),
    "vencimiento_posterior_a_la_migracion": (
        _cambiar(3, 2, date(2026, 10, 20)),
        ("Saldos", 3, "Vencimiento"),
    ),
    "vencimiento_vacio_con_periodo": (_cambiar(3, 2, None), ("Saldos", 3, "Vencimiento")),
    "dos_vencimientos_en_un_periodo": (
        _cambiar(5, 2, date(2026, 9, 15)),
        ("Saldos", 5, "Vencimiento"),
    ),
    "concepto_fuera_del_vocabulario": (_cambiar(3, 3, "Expensa"), ("Saldos", 3, "Concepto")),
    "importe_con_tres_decimales": (_cambiar(3, 4, "85000.123"), ("Saldos", 3, "Importe")),
    "importe_ambiguo": (_cambiar(3, 4, "1.234"), ("Saldos", 3, "Importe")),
    "interes_negativo": (_cambiar(2, 5, "-1.00"), ("Saldos", 2, "Interés acumulado")),
    "periodo_con_capital_cero_y_solo_interes": (
        _agregar(["1A", "2026-07", date(2026, 7, 10), "Ordinaria", "0.00", "500.00"]),
        ("Saldos", 9, "Interés acumulado"),
    ),
    "unidad_que_mezcla_detalle_y_total": (
        _agregar(["1A", None, None, None, "1000.00", None]),
        ("Saldos", 9, "Período"),
    ),
    "credito_con_periodo": (_cambiar(7, 1, "2026-09"), ("Saldos", 7, "Período")),
    "credito_con_concepto": (_cambiar(8, 3, "Ordinaria"), ("Saldos", 8, "Concepto")),
}


@pytest.mark.parametrize("caso", sorted(CASOS_DE_SALDOS))
def test_c13_fila_de_saldos_invalida(mundo: Mundo, caso: str) -> None:
    """Escenario: Unidad que no existe
    Escenario: Vencimiento posterior a la migración
    Escenario: Mismo período con dos vencimientos
    Escenario: Mezcla de detalle y total"""
    cambio, esperado = CASOS_DE_SALDOS[caso]
    antes = conteos(mundo)
    respuesta = importar(mundo, archivo(cambio(saldos_base())))
    lugares = ubicaciones(errores(respuesta))
    assert esperado in lugares, f"{caso}: se esperaba un error en {esperado}, llegaron {lugares}"
    assert conteos(mundo) == antes, f"{caso}: un rechazo no escribe nada"


def test_c13_todos_los_errores_juntos(mundo: Mundo) -> None:
    saldos = saldos_base()
    saldos[0][0] = "9Z"  # fila 2: unidad inexistente
    saldos[1][3] = "Expensa"  # fila 3: concepto
    saldos[4][4] = "1.234"  # fila 6: importe ambiguo
    antes = conteos(mundo)
    lugares = ubicaciones(errores(importar(mundo, archivo(saldos))))
    esperados = {("Saldos", 2, "Unidad"), ("Saldos", 3, "Concepto"), ("Saldos", 6, "Importe")}
    assert esperados <= lugares, f"los tres errores juntos: {lugares}"
    assert conteos(mundo) == antes


# --- C14 · Hojas ----------------------------------------------------------------------------------


def test_c14_saldos_sin_control(mundo: Mundo) -> None:
    antes = conteos(mundo)
    lista = errores(importar(mundo, archivo(sin_control=True)))
    assert any(e.hoja == "Control" and e.fila is None for e in lista) or any(
        "Control" in e.motivo and e.fila is None for e in lista
    ), f"falta la hoja Control: es error de archivo que la nombra: {lista}"
    assert conteos(mundo) == antes


def test_c14_control_con_unidad_inexistente(mundo: Mundo) -> None:
    control = [*control_base(), ["9Z", "100.00"]]
    antes = conteos(mundo)
    lugares = ubicaciones(errores(importar(mundo, archivo(control=control))))
    assert ("Control", 7, "Unidad") in lugares, lugares
    assert conteos(mundo) == antes


def test_c14_control_con_unidad_repetida(mundo: Mundo) -> None:
    control = [*control_base(), ["1A", "169000.00"]]
    antes = conteos(mundo)
    lista = errores(importar(mundo, archivo(control=control)))
    repetida = [e for e in lista if (e.hoja, e.fila, e.columna) == ("Control", 7, "Unidad")]
    assert repetida, f"la fila 7 repite 1A: {lista}"
    assert "2" in repetida[0].motivo, f"el motivo nombra la otra fila (2): {repetida[0].motivo}"
    assert conteos(mundo) == antes


@pytest.mark.parametrize(
    ("hoja", "falta"),
    [
        ("Saldos", "Importe"),
        ("Saldos", "Unidad"),
        ("Control", "Saldo según el administrador"),
        ("Control", "Unidad"),
    ],
)
def test_c14_encabezado_faltante(mundo: Mundo, hoja: str, falta: str) -> None:
    if hoja == "Saldos":
        encabezados = [c for c in ENC_SALDOS if c != falta]
        indice = ENC_SALDOS.index(falta)
        saldos = [[v for i, v in enumerate(f) if i != indice] for f in saldos_base()]
        contenido = archivo(saldos, enc_saldos=encabezados)
    else:
        encabezados = [c for c in ENC_CONTROL if c != falta]
        indice = ENC_CONTROL.index(falta)
        control = [[v for i, v in enumerate(f) if i != indice] for f in control_base()]
        contenido = archivo(control=control, enc_control=encabezados)
    antes = conteos(mundo)
    lista = errores(importar(mundo, contenido))
    assert any(e.hoja == hoja and e.fila is None and e.columna == falta for e in lista), (
        f"falta {falta} en {hoja}: error de archivo (fila nula) que la nombra: {lista}"
    )
    assert conteos(mundo) == antes
