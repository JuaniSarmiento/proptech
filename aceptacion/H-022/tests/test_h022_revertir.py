"""H-022 · revertir un pago confirmado (C01 a C06, N01 a N06). Contrato en `aceptacion/H-022/CONTRATO.md`.

Escenario de P29 (HISTORIAS.md, H-022): `1A` y `1B` deben $100.000 de octubre. `1A` transfiere $100.000 el 05/11 y
se confirma antes de la emisión de diciembre, que le cobra $552,50 con el pago adentro (a `1B`, que no pagó,
$3.000). Revertir el 10/12 tiene que dejar a `1A` igual al centavo que `1B`: un `interes_por_reversion` de $2.447,50.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from ._h022 import (
    NOV,
    OCT,
    Mundo,
    anular,
    auditorias,
    campo_422,
    conflicto_de_estado,
    confirmar,
    cuenta_de,
    emitir,
    emitir_noviembre,
    en_paralelo,
    estado,
    eventos,
    informar_ok,
    informar_y_confirmar,
    interes_de,
    listar,
    movimientos,
    rechazar,
    residuales_por_periodo,
    revertir,
    situacion_de,
)

DIC = date(2026, 12, 1)
ENE = date(2027, 1, 1)


def _ok(r: Any, pago: str) -> None:
    assert r.status_code == 200, f"revertir: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"pago_id": pago, "estado": "revertido"}, r.json()


def _p29(m: Mundo) -> tuple[str, Any]:
    """`1A` paga a tiempo; `1B` no paga. Devuelve el pago de `1A` y la emisión de diciembre."""
    emitir(m, OCT, {"1A": "100000.00", "1B": "100000.00"})
    emitir(m, NOV, {"1A": "1000.00", "1B": "1000.00"})
    pago = informar_y_confirmar(m, {"1A": "100000.00"}, fecha="2026-11-05", numero="p29-1a")
    diciembre = emitir(m, DIC, {"1A": "1000.00", "1B": "1000.00"})
    return pago, diciembre


# --- C01: revertir -------------------------------------------------------------------------------------


def test_c01_cheque_rechazado(mundo: Mundo) -> None:
    """Escenario: Cheque rechazado"""
    emitir_noviembre(mundo)
    deuda_antes = estado(mundo, "1A").deuda
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    assert estado(mundo, "1A").deuda.a_texto() == "0.00"
    _ok(revertir(mundo, pago, "Cheque rechazado, fondos insuficientes"), pago)
    del_pago = movimientos(mundo, "1A", "pago")
    reversiones = movimientos(mundo, "1A", "reversion_de_pago")
    assert len(del_pago) == 1 and len(reversiones) == 1, (del_pago, reversiones)
    assert reversiones[0][1] == "43350.00" and reversiones[0][2] == del_pago[0][0], (
        f"la reversión corrige el pago por su importe: {reversiones}"
    )
    assert estado(mundo, "1A").deuda == deuda_antes, "la deuda no volvió a la de antes del pago"
    assert ("revertido", "Cheque rechazado, fondos insuficientes") in eventos(mundo, pago)
    assert auditorias(mundo, "revertir_pago_informado") == 1
    papeles = sorted(f[0] for f in mundo.filas("SELECT papel FROM movimiento_de_pago WHERE pago_id = %s", (pago,)))
    assert papeles == ["pago", "reversion_de_pago"], papeles
    mundo.como("ana")
    visto = {p["pago_id"]: (p["estado"], p["motivo"]) for p in listar(mundo)}
    assert visto[pago] == ("revertido", "Cheque rechazado, fondos insuficientes"), visto


# --- C02: P29 ----------------------------------------------------------------------------------------


def test_c02_revertir_despues_de_una_emision(mundo: Mundo) -> None:
    """Escenario: Revertir después de una emisión"""
    pago, diciembre = _p29(mundo)
    _ok(revertir(mundo, pago), pago)
    extra = movimientos(mundo, "1A", "interes_por_reversion")
    assert [(i, e) for _, i, _, e in extra] == [("2447.50", interes_de(mundo, "1A", diciembre, OCT))], (
        f"diciembre cobró $552,50 con el pago adentro; sin él son $3.000: {extra}"
    )
    a, b = residuales_por_periodo(mundo, "1A"), residuales_por_periodo(mundo, "1B")
    assert a == b, f"1A revertido tiene que quedar como 1B, que nunca pagó: 1A {a}, 1B {b}"


# --- C03: el ajuste se revierte con el pago -------------------------------------------------------------


def test_c03_revierte_el_ajuste(mundo: Mundo) -> None:
    emitir(mundo, OCT, {"1A": "100000.00", "1B": "100000.00"})
    emitir(mundo, NOV, {"1A": "1000.00", "1B": "1000.00"})
    emitir(mundo, DIC, {"1A": "1000.00", "1B": "1000.00"})
    pago = informar_y_confirmar(mundo, {"1A": "100000.00"}, fecha="2026-11-05", numero="tarde-1a")
    (ajuste,) = movimientos(mundo, "1A", "ajuste_de_interes")
    _ok(revertir(mundo, pago), pago)
    contra = [f for f in mundo.filas("SELECT id FROM movimiento WHERE corrige_a = %s", (ajuste[0],))]
    assert len(contra) == 1, "el ajuste enlazado al pago tiene que revertirse con un contra-asiento"
    assert movimientos(mundo, "1A", "interes_por_reversion") == [], (
        "sin el pago, diciembre queda en lo que cobró ($3.000): no hay interés por reversión"
    )
    assert residuales_por_periodo(mundo, "1A") == residuales_por_periodo(mundo, "1B")


# --- C04: moroso crítico -------------------------------------------------------------------------------


def test_c04_revertir_pasa_a_moroso_critico(mundo: Mundo) -> None:
    """Escenario: Revertir pasa a moroso crítico"""
    emitir(mundo, OCT, {"1A": "100000.00"})
    emitir(mundo, NOV, {"1A": "1000.00"})
    pago = informar_y_confirmar(mundo, {"1A": "103100.00"}, fecha="2026-11-05", numero="todo")
    assert situacion_de(mundo, "1A").moroso_critico is False, "con todo pagado no es moroso crítico"
    _ok(revertir(mundo, pago), pago)
    s = situacion_de(mundo, "1A")
    assert s.moroso_critico is True and s.liquidaciones_vencidas == 2, (
        f"octubre y noviembre vuelven a estar vencidas con capital impago: {s}"
    )


# --- C05: un pago repartido ----------------------------------------------------------------------------


def test_c05_revierte_todas_las_partes(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    antes = {u: estado(mundo, u).deuda for u in ("1A", "2B")}
    pago = informar_y_confirmar(mundo, {"1A": "43350.00", "2B": "37425.00"})
    _ok(revertir(mundo, pago), pago)
    for u in ("1A", "2B"):
        assert len(movimientos(mundo, u, "reversion_de_pago")) == 1, u
        assert estado(mundo, u).deuda == antes[u], u


# --- C06: el interés por reversión sigue a su interés -------------------------------------------------


def test_c06_anular_la_emision_lo_deja_fuera(mundo: Mundo) -> None:
    pago, diciembre = _p29(mundo)
    _ok(revertir(mundo, pago), pago)
    (extra,) = movimientos(mundo, "1A", "interes_por_reversion")
    anular(mundo, diciembre)
    assert extra[0] not in estado(mundo, "1A").movimientos_que_cuentan, "el interés por reversión de un interés anulado cuenta"
    assert residuales_por_periodo(mundo, "1A") == residuales_por_periodo(mundo, "1B")


# --- N01: sólo un confirmado se revierte ---------------------------------------------------------------


def test_n01_revertir_uno_no_confirmado(mundo: Mundo) -> None:
    """Escenario: Revertir uno no confirmado"""
    emitir_noviembre(mundo)
    mundo.como("ana")
    informado = informar_ok(mundo, {"1A": "43350.00"}, numero="sin-confirmar")
    rechazado = informar_ok(mundo, {"2B": "37425.00"}, numero="rechazado")
    mundo.como("admin_principal")
    assert rechazar(mundo, rechazado).status_code == 200
    conflicto_de_estado(revertir(mundo, informado))
    conflicto_de_estado(revertir(mundo, rechazado))
    confirmado = informar_y_confirmar(mundo, {"1A": "43350.00"}, numero="dos-veces")
    _ok(revertir(mundo, confirmado), confirmado)
    conflicto_de_estado(revertir(mundo, confirmado))
    conflicto_de_estado(confirmar(mundo, confirmado))
    assert len(movimientos(mundo, "1A", "reversion_de_pago")) == 1


# --- N02: el motivo ------------------------------------------------------------------------------------


@pytest.mark.parametrize("motivo", [None, "", "ab", "x" * 501])
def test_n02_revertir_sin_motivo_valido(mundo: Mundo, motivo: Any) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    assert campo_422(revertir(mundo, pago, motivo)) == "motivo"
    assert movimientos(mundo, "1A", "reversion_de_pago") == []


# --- N03: el pago original no cambia --------------------------------------------------------------------


def test_n03_el_original_no_cambia(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    fila = mundo.filas("SELECT * FROM pago_informado WHERE id = %s", (pago,))
    movimiento = mundo.filas("SELECT * FROM movimiento WHERE cuenta_id = %s AND tipo = 'pago'", (cuenta_de(mundo, "1A"),))
    _ok(revertir(mundo, pago), pago)
    assert mundo.filas("SELECT * FROM pago_informado WHERE id = %s", (pago,)) == fila
    assert mundo.filas("SELECT * FROM movimiento WHERE cuenta_id = %s AND tipo = 'pago'",
                       (cuenta_de(mundo, "1A"),)) == movimiento
    assert eventos(mundo, pago)[0] == ("confirmado", None), "el evento confirmado sigue en la historia"


# --- N04: el interés por reversión no genera interés ---------------------------------------------------


def test_n04_no_hay_interes_sobre_interes(mundo: Mundo) -> None:
    pago, _ = _p29(mundo)
    _ok(revertir(mundo, pago), pago)
    emitir(mundo, ENE, {"1A": "1000.00", "1B": "1000.00"})
    a, b = residuales_por_periodo(mundo, "1A"), residuales_por_periodo(mundo, "1B")
    assert a == b, f"en enero 1A pagaría interés sobre el interés por reversión: 1A {a}, 1B {b}"


# --- N05: sin permiso ----------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["admin_del_edificio", "ana", "consejo", "contador", "auxiliar"])
def test_n05_sin_permiso(mundo: Mundo, rol: str) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    mundo.como(rol)
    r = revertir(mundo, pago)
    assert r.status_code == 403, f"{rol}: se esperaba 403, llegó {r.status_code}: {r.text[:200]}"
    assert movimientos(mundo, "1A", "reversion_de_pago") == []


# --- N06: en carrera ------------------------------------------------------------------------------------


def test_n06_revertir_en_carrera(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    respuestas = en_paralelo(lambda: revertir(mundo, pago), lambda: revertir(mundo, pago))
    codigos = sorted(getattr(r, "status_code", repr(r)) for r in respuestas)
    assert codigos == [200, 409], f"una gana y la otra da 409: {codigos}"
    assert len(movimientos(mundo, "1A", "reversion_de_pago")) == 1
