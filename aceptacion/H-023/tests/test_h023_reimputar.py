"""H-023 · reimputar un pago a la unidad correcta (C01 a C05, N01 a N05). Contrato en `aceptacion/H-023/CONTRATO.md`.

Escenario base: la expensa de noviembre emitida (`1A` $43.350, `1B` $48.350). Beto informa por error para `1B` un pago
de $43.350 que era de `1A`; se confirma y después se reimputa de `1B` a `1A`.
"""

from __future__ import annotations

import importlib
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from ._h023 import (
    NOV,
    OCT,
    Mundo,
    auditorias,
    campo_422,
    conflicto_de_estado,
    emitir,
    emitir_noviembre,
    en_paralelo,
    estado,
    eventos,
    informar_ok,
    informar_y_confirmar,
    listar,
    movimientos,
    reimputar,
    residuales_por_periodo,
    revertir,
    situacion_de,
)

DIC = date(2026, 12, 1)
MOTIVO = "El vecino de 1A cargó el pago a 1B"


def _ok(r: Any, pago: str) -> None:
    assert r.status_code == 200, f"reimputar: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"pago_id": pago, "estado": "confirmado"}, r.json()


def _pago_en_1b(m: Mundo) -> str:
    emitir_noviembre(m)
    return informar_y_confirmar(m, {"1B": "43350.00"}, numero="en-1b")


# --- C01: de 1B a 1A ---------------------------------------------------------------------------------


def test_c01_de_1b_a_1a(mundo: Mundo) -> None:
    """Escenario: De 7B a 7A"""
    emitir_noviembre(mundo)
    deuda_1b = estado(mundo, "1B").deuda
    pago = informar_y_confirmar(mundo, {"1B": "43350.00"}, numero="en-1b")
    _ok(reimputar(mundo, pago, "1B", "1A", MOTIVO), pago)
    (del_pago,) = movimientos(mundo, "1B", "pago")
    debitos = movimientos(mundo, "1B", "reimputacion")
    assert len(debitos) == 1 and debitos[0][1] == "43350.00" and debitos[0][2] == del_pago[0], (
        f"en 1B, un `reimputacion` que corrige el pago por su importe: {debitos}"
    )
    assert estado(mundo, "1B").deuda == deuda_1b, "1B tiene que volver a deber lo de antes del pago"
    creditos = movimientos(mundo, "1A", "reimputacion")
    assert len(creditos) == 1 and creditos[0][1] == "43350.00" and creditos[0][3] == debitos[0][0], (
        f"en 1A, un `reimputacion` por el importe, enlazado al débito de 1B: {creditos}"
    )
    fecha = mundo.uno("SELECT fecha_valor FROM movimiento WHERE id = %s", (creditos[0][0],))
    assert fecha == date(2026, 11, 5), f"el crédito de 1A vale con la fecha de la transferencia: {fecha}"
    assert estado(mundo, "1A").deuda.a_texto() == "0.00"
    assert ("reimputado", MOTIVO) in eventos(mundo, pago)
    assert auditorias(mundo, "reimputar_pago_informado") == 1
    assert {p["pago_id"]: p["estado"] for p in listar(mundo)}[pago] == "confirmado"
    papeles = sorted(f[0] for f in mundo.filas("SELECT papel FROM movimiento_de_pago WHERE pago_id = %s", (pago,)))
    assert papeles == ["pago", "reimputacion", "reimputacion"], papeles


# --- C02: la situación de las dos ------------------------------------------------------------------------


def test_c02_la_situacion_de_las_dos(mundo: Mundo) -> None:
    pago = _pago_en_1b(mundo)
    _ok(reimputar(mundo, pago, "1B", "1A"), pago)
    a, b = situacion_de(mundo, "1A"), situacion_de(mundo, "1B")
    assert a.total_vencido.a_texto() == "0.00", f"1A quedó pagada: {a}"
    assert b.total_vencido.a_texto() == "48350.00" and b.liquidaciones_vencidas == 1, f"1B vuelve a deber noviembre: {b}"


# --- C03: con una emisión de por medio ------------------------------------------------------------------


def test_c03_con_una_emision_de_por_medio(mundo: Mundo) -> None:
    todas = {u: "100000.00" for u in ("1A", "1B", "2A", "2B")}
    emitir(mundo, OCT, todas)
    emitir(mundo, NOV, {u: "1000.00" for u in todas})
    pago = informar_y_confirmar(mundo, {"1B": "100000.00"}, fecha="2026-11-05", numero="en-1b")
    informar_y_confirmar(mundo, {"2B": "100000.00"}, fecha="2026-11-05", numero="2b-a-tiempo")
    emitir(mundo, DIC, {u: "1000.00" for u in todas})
    _ok(reimputar(mundo, pago, "1B", "1A"), pago)
    assert [i for _, i, _, _ in movimientos(mundo, "1B", "interes_por_reversion")] == ["2447.50"], (
        "1B recibe el interés de diciembre que se le cobró de menos con el pago adentro"
    )
    assert [i for i, _ in ((m[1], m[3]) for m in movimientos(mundo, "1A", "ajuste_de_interes"))] == ["2447.50"], (
        "1A recibe el ajuste del interés de diciembre que se le cobró de más"
    )
    assert residuales_por_periodo(mundo, "1B") == residuales_por_periodo(mundo, "2A"), "1B tiene que quedar como 2A, que nunca pagó"
    assert residuales_por_periodo(mundo, "1A") == residuales_por_periodo(mundo, "2B"), "1A tiene que quedar como 2B, que pagó a tiempo"


# --- C04: reimputar de nuevo ---------------------------------------------------------------------------


def test_c04_reimputar_de_nuevo(mundo: Mundo) -> None:
    pago = _pago_en_1b(mundo)
    _ok(reimputar(mundo, pago, "1B", "1A"), pago)
    (credito_1a,) = movimientos(mundo, "1A", "reimputacion")
    _ok(reimputar(mundo, pago, "1A", "2A", "Tampoco era de 1A"), pago)
    debitos_1a = [m for m in movimientos(mundo, "1A", "reimputacion") if m[0] != credito_1a[0]]
    assert len(debitos_1a) == 1 and debitos_1a[0][2] == credito_1a[0], (
        f"el segundo débito corrige el crédito de 1A: {debitos_1a}"
    )
    assert estado(mundo, "1A").deuda.a_texto() == "43350.00"
    assert len(movimientos(mundo, "2A", "reimputacion")) == 1


# --- C05: revertir después de reimputar ------------------------------------------------------------------


def test_c05_revertir_un_reimputado(mundo: Mundo) -> None:
    pago = _pago_en_1b(mundo)
    _ok(reimputar(mundo, pago, "1B", "1A"), pago)
    (credito_1a,) = movimientos(mundo, "1A", "reimputacion")
    r = revertir(mundo, pago)
    assert r.status_code == 200, r.text[:300]
    reversiones = movimientos(mundo, "1A", "reversion_de_pago")
    assert len(reversiones) == 1 and reversiones[0][2] == credito_1a[0], (
        f"revertir corrige el movimiento vigente (el crédito de 1A): {reversiones}"
    )
    assert movimientos(mundo, "1B", "reversion_de_pago") == [], "el pago ya no estaba en 1B"
    assert estado(mundo, "1A").deuda.a_texto() == "43350.00"


# --- N01: falla a mitad --------------------------------------------------------------------------------


def test_n01_falla_a_mitad_de_camino(mundo: Mundo, monkeypatch: pytest.MonkeyPatch) -> None:
    """Escenario: Falla a mitad de camino"""
    pago = _pago_en_1b(mundo)
    try:
        libro = importlib.import_module("proptech_core.cuenta_corriente.aplicacion.pagos")
    except ImportError as error:
        raise AssertionError(f"falta `cuenta_corriente.aplicacion.pagos`: {error}") from None
    assert getattr(libro, "registrar_pago", None) is not None, "falta `registrar_pago`"
    llamadas: list[int] = []

    def falla(*args: Any, **kwargs: Any) -> Any:
        llamadas.append(1)
        raise RuntimeError("falla inyectada en el destino")

    monkeypatch.setattr(libro, "registrar_pago", falla)
    antes = {u: len(mundo.filas("SELECT 1 FROM movimiento WHERE cuenta_id = (SELECT id FROM cuenta WHERE "
                                 "unidad_id = %s)", (mundo.unidades[u],))) for u in ("1A", "1B")}
    r = reimputar(mundo, pago, "1B", "1A")
    assert r.status_code == 500, f"la falla inyectada llega como 500: {r.status_code} {r.text[:200]}"
    assert llamadas, "el destino tiene que registrarse con `registrar_pago`"
    despues = {u: len(mundo.filas("SELECT 1 FROM movimiento WHERE cuenta_id = (SELECT id FROM cuenta WHERE "
                                   "unidad_id = %s)", (mundo.unidades[u],))) for u in ("1A", "1B")}
    assert despues == antes, f"quedó un movimiento en alguna de las dos cuentas: antes {antes}, después {despues}"
    assert eventos(mundo, pago) == [("confirmado", None)] and auditorias(mundo, "reimputar_pago_informado") == 0


# --- N02: los pedidos que no van -----------------------------------------------------------------------


def test_n02_validaciones(mundo: Mundo) -> None:
    pago = _pago_en_1b(mundo)
    assert campo_422(reimputar(mundo, pago, "1B", "1B")) == "hacia_unidad_id"
    assert campo_422(reimputar(mundo, pago, "2A", "1A")) == "desde_unidad_id"
    r = reimputar(mundo, pago, "1B", mundo.unidad_otro)
    assert r.status_code == 404 and r.json() == {"detail": "no encontrado"}, r.text[:200]
    r = reimputar(mundo, pago, "1B", uuid4())
    assert r.status_code == 404, r.text[:200]
    mundo.como("beto")
    informado = informar_ok(mundo, {"1B": "100.00"}, numero="solo-informado")
    mundo.como("admin_principal")
    conflicto_de_estado(reimputar(mundo, informado, "1B", "1A"))
    assert revertir(mundo, pago).status_code == 200
    conflicto_de_estado(reimputar(mundo, pago, "1B", "1A"))
    assert movimientos(mundo, "1A", "reimputacion") == []


# --- N03: el motivo ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("motivo", [None, "", "ab", "x" * 501])
def test_n03_sin_motivo_valido(mundo: Mundo, motivo: Any) -> None:
    pago = _pago_en_1b(mundo)
    assert campo_422(reimputar(mundo, pago, "1B", "1A", motivo)) == "motivo"
    assert movimientos(mundo, "1B", "reimputacion") == []


# --- N04: en carrera ------------------------------------------------------------------------------------


def test_n04_dos_reimputaciones_en_carrera(mundo: Mundo) -> None:
    pago = _pago_en_1b(mundo)
    respuestas = en_paralelo(lambda: reimputar(mundo, pago, "1B", "1A"), lambda: reimputar(mundo, pago, "1B", "2A"))
    codigos = sorted(getattr(r, "status_code", 0) for r in respuestas)
    assert codigos[0] == 200 and codigos[1] in (409, 422), f"una gana y la otra no escribe: {codigos}"
    assert len(movimientos(mundo, "1B", "reimputacion")) == 1
    destinos = len(movimientos(mundo, "1A", "reimputacion")) + len(movimientos(mundo, "2A", "reimputacion"))
    assert destinos == 1, "quedaron dos créditos de destino"
    total = sum((estado(mundo, u).deuda.decimal for u in ("1A", "1B", "2A")), Decimal(0))
    assert total == Decimal("43350.00") + Decimal("48350.00") + Decimal("62375.00") - Decimal("43350.00")


# --- N05: sin permiso -----------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["admin_del_edificio", "beto", "consejo", "contador"])
def test_n05_sin_permiso(mundo: Mundo, rol: str) -> None:
    pago = _pago_en_1b(mundo)
    mundo.como(rol)
    r = reimputar(mundo, pago, "1B", "1A")
    assert r.status_code == 403, f"{rol}: se esperaba 403, llegó {r.status_code}: {r.text[:200]}"
    mundo.como("admin_principal")
    assert movimientos(mundo, "1B", "reimputacion") == []
