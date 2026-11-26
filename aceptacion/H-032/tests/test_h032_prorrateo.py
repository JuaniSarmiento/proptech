"""H-032 · prorrateo por días de la expensa del mes del cambio (C01 a C06).

Cada test lleva su criterio en el nombre. Los montos se verifican contra el libro (`obligacion`, `movimiento`,
`estado_de_cuenta`), componente por componente, con el redondeo medio hacia arriba para el vendedor. Hoy la ruta de
H-030 contesta 422 a `expensa_del_mes: "prorrateo"`: cada test falla por aserción (el 201 que espera).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from ._h032 import (
    A_NOMBRE,
    CLAVES_DEL_CAMBIO,
    CLAVES_DEL_TRASLADO,
    COMPONENTES,
    Mundo,
    cargar_gastos,
    comprobar_el_mes,
    con_prorrateo,
    cuenta_de,
    cuenta_del_vendedor,
    cuentas_de_persona,
    del_libro,
    del_mes,
    desglose,
    deuda_de_cuenta,
    el_prorrateo,
    emitir_por_la_api,
    en_el_get,
    impago_del_mes,
    movimientos,
    mundo_emitido,
    no_procesable,
    pagar,
    partes_esperadas,
    registrar,
    registrar_ok,
    residuales_anteriores,
    sembrar_anteriores,
    todo,
    total,
    traslados,
    traslados_del_mes,
)

MONTO = re.compile(r"^[0-9]+\.[0-9]{2}$")
D = Decimal


def _texto(valor: Decimal) -> str:
    return format(valor, ".2f")


# --- C01: la opción y la respuesta ---------------------------------------------------------------------


def test_c01_pendiente_responde_201_con_su_forma(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-11")
    assert set(cambio) == CLAVES_DEL_CAMBIO | {"prorrateo"}, f"claves de la respuesta: {sorted(cambio)}"
    assert cambio["expensa_del_mes"] == "prorrateo" and cambio["deuda_previa"] == "en_la_unidad", cambio
    assert el_prorrateo(cambio) == {"estado": "pendiente", "periodo": "2026-11-01", "dias_del_vendedor": 10,
                                    "dias_del_mes": 30, "parte_del_vendedor": None}, cambio["prorrateo"]
    assert traslados(mundo) == [] and cuentas_de_persona(mundo, ana) == [], "pendiente: nada en el libro todavía"
    guardada = en_el_get(mundo, "1A")
    assert [c["prorrateo"] for c in guardada] == [cambio["prorrateo"]], "el GET trae lo mismo que el 201"


def test_c01_aplicado_responde_201_con_su_forma(mundo: Mundo) -> None:
    ana, carla = mundo.personas["ana"], mundo.personas["carla"]
    mundo_emitido(mundo)
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-11")
    parte = total(partes_esperadas(mundo, "1A", 10, 30))
    assert set(cambio) == CLAVES_DEL_CAMBIO | {"prorrateo"}, f"sin `trasladado` ni cuenta: {sorted(cambio)}"
    assert el_prorrateo(cambio) == {"estado": "aplicado", "periodo": "2026-11-01", "dias_del_vendedor": 10,
                                    "dias_del_mes": 30, "parte_del_vendedor": _texto(parte)}, cambio["prorrateo"]
    assert isinstance(cambio["prorrateo"]["parte_del_vendedor"], str) and parte > 0
    assert MONTO.match(cambio["prorrateo"]["parte_del_vendedor"])
    assert [c["prorrateo"] for c in en_el_get(mundo, "1A")] == [cambio["prorrateo"]], "el GET trae lo mismo"
    entera = registrar_ok(mundo, "1B", [carla], fecha="2026-11-11")
    assert "prorrateo" not in entera and entera["expensa_del_mes"] == "entera", "sin prorrateo no hay `prorrateo`"
    assert all("prorrateo" not in c for c in en_el_get(mundo, "1B"))


def test_c01_con_dos_vendedores_la_parte_va_al_deudor_elegido(mundo: Mundo) -> None:
    dora, edu = mundo.personas["dora"], mundo.personas["edu"]
    mundo_emitido(mundo)
    antes = todo(mundo)
    no_procesable(registrar(mundo, "2A", [dora, edu], fecha="2026-11-11", expensa_del_mes="prorrateo"))
    assert todo(mundo) == antes, "sin `vendedor_deudor` y con dos vendedores: 422 y no queda nada"
    cambio = con_prorrateo(mundo, "2A", [dora, edu], "2026-11-11", vendedor_deudor=str(edu))
    assert cuentas_de_persona(mundo, dora) == [], "Dora no es la deudora: no tiene cuenta"
    comprobar_el_mes(mundo, "2A", edu, el_prorrateo(cambio), 10, 30)


# --- C02: cada componente se parte al centavo ----------------------------------------------------------


@pytest.mark.parametrize(("unidad", "quien", "fecha", "dias"), [
    ("1A", "ana", "2026-11-11", 10),
    ("1A", "ana", "2026-11-16", 15),
    ("1B", "carla", "2026-11-16", 15),
    ("1B", "carla", "2026-11-30", 29),
])
def test_c02_cada_componente_se_parte_al_centavo(mundo: Mundo, unidad: str, quien: str, fecha: str,
                                                 dias: int) -> None:
    mundo_emitido(mundo)
    comp = del_mes(mundo, unidad)
    if dias == 15:
        assert any(int(v * 100) % 2 == 1 for v in comp.values()), f"precondición: hay mitades de centavo: {comp}"
    cambio = con_prorrateo(mundo, unidad, [mundo.personas[quien]], fecha)
    comprobar_el_mes(mundo, unidad, mundo.personas[quien], el_prorrateo(cambio), dias, 30)
    deuda = deuda_de_cuenta(mundo, cuenta_de(mundo, unidad))
    assert cambio["aviso"] == ({"deuda": _texto(deuda)} if deuda > 0 else None), (
        f"el aviso es lo que le queda a la unidad después del traslado: {cambio['aviso']} contra {deuda}")


def test_c02_los_importes_del_ejemplo_con_redondeo_medio_hacia_arriba(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    mundo_emitido(mundo)
    assert del_mes(mundo, "1A") == {"ordinaria": D("30000.31"), "fondo_de_reserva": D("1500.02"),
                                    "extraordinaria": D("15000.01")}, "precondición: la obligación de `1A`"
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-16")
    assert traslados_del_mes(mundo, "1A") == {"ordinaria": D("15000.16"), "fondo_de_reserva": D("750.01"),
                                              "extraordinaria": D("7500.01")}, "15 de 30, medio centavo hacia arriba"
    assert impago_del_mes(mundo, "1A") == {"ordinaria": D("15000.15"), "fondo_de_reserva": D("750.01"),
                                           "extraordinaria": D("7500.00")}, "la unidad se queda con el resto"
    assert cambio["prorrateo"]["parte_del_vendedor"] == "23250.18", cambio["prorrateo"]


# --- C03: los días del vendedor -------------------------------------------------------------------------


def test_c03_los_dias_del_vendedor_son_los_anteriores_a_la_fecha(mundo: Mundo) -> None:
    ana, carla, dora = mundo.personas["ana"], mundo.personas["carla"], mundo.personas["dora"]
    esperados = [
        ("1A", [ana], "2026-11-11", ("2026-11-01", 10, 30)),
        ("1B", [carla], "2026-11-30", ("2026-11-01", 29, 30)),
        ("2B", [ana], "2026-11-01", ("2026-11-01", 0, 30)),
        ("2A", [dora], "2026-12-15", ("2026-12-01", 14, 31)),
    ]
    for unidad, vendedores, fecha, (periodo, dias, del_mes_) in esperados:
        p = el_prorrateo(con_prorrateo(mundo, unidad, vendedores, fecha))
        assert (p["periodo"], p["dias_del_vendedor"], p["dias_del_mes"]) == (periodo, dias, del_mes_), (fecha, p)
        assert p["estado"] == "pendiente", "el período no está emitido"


def test_c03_con_fecha_el_dia_1_la_parte_es_cero_y_no_hay_movimientos(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    mundo_emitido(mundo)
    libro = del_libro(mundo)
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-01")
    assert el_prorrateo(cambio) == {"estado": "aplicado", "periodo": "2026-11-01", "dias_del_vendedor": 0,
                                    "dias_del_mes": 30, "parte_del_vendedor": "0.00"}, cambio["prorrateo"]
    assert del_libro(mundo) == libro, "el libro no cambia: ni movimientos ni cuenta de persona"
    assert traslados(mundo) == [] and cuentas_de_persona(mundo, ana) == []


def test_c03_febrero_bisiesto_cuenta_29_dias(mundo: Mundo) -> None:
    from proptech_api.morosidad import hoy

    mundo.app.dependency_overrides[hoy] = lambda: date(2028, 3, 1)
    febrero = date(2028, 2, 1)
    mundo_emitido(mundo, febrero)
    ana = mundo.personas["ana"]
    cambio = con_prorrateo(mundo, "1A", [ana], "2028-02-11")
    assert (cambio["prorrateo"]["dias_del_vendedor"], cambio["prorrateo"]["dias_del_mes"]) == (10, 29)
    comprobar_el_mes(mundo, "1A", ana, el_prorrateo(cambio), 10, 29, periodo=febrero)


# --- C04: el período todavía no está emitido -----------------------------------------------------------


def test_c04_el_prorrateo_pendiente_se_aplica_al_emitir_el_periodo(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    cargar_gastos(mundo)
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-11")
    assert cambio["prorrateo"]["estado"] == "pendiente" and cambio["prorrateo"]["parte_del_vendedor"] is None
    assert traslados(mundo) == [] and cuentas_de_persona(mundo, ana) == [], "pendiente: nada en el libro"
    emitir_por_la_api(mundo)
    aplicado = en_el_get(mundo, "1A")[0]["prorrateo"]
    comprobar_el_mes(mundo, "1A", ana, aplicado, 10, 30)
    assert {UUID(str(t[1])) for t in traslados(mundo)} == {cuenta_de(mundo, "1A"), *cuentas_de_persona(mundo, ana)}, (
        "sólo se movió la unidad vendida y la cuenta del vendedor")


def test_c04_repetir_la_emision_no_traslada_dos_veces(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    cargar_gastos(mundo)
    con_prorrateo(mundo, "1A", [ana], "2026-11-11")
    primera = emitir_por_la_api(mundo)
    libro = del_libro(mundo)
    r = mundo.cliente.post(f"/api/complejos/{mundo.edificio}/periodos/2026-11-01/emision",
                           json={"emision_id": primera["emision_id"], "huella": primera["huella"],
                                 "alertas_aceptadas": []})
    assert r.status_code == 200, f"el mismo pedido otra vez da 200: {r.status_code} {r.text[:200]}"
    assert del_libro(mundo) == libro, "la repetición no escribe nada"
    comprobar_el_mes(mundo, "1A", ana, en_el_get(mundo, "1A")[0]["prorrateo"], 10, 30)


# --- C05: prorrateo y deuda a nombre del vendedor, juntos ----------------------------------------------


def test_c05_prorrateo_y_deuda_a_nombre_del_vendedor_dan_las_dos_cosas(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    sembrar_anteriores(mundo)
    mundo_emitido(mundo)
    antes = desglose(mundo, "1A")
    assert antes["previo"] > 0 and antes["posterior"] > 0, f"precondición: deuda anterior y expensa del mes: {antes}"
    deuda_unidad = deuda_de_cuenta(mundo, cuenta_de(mundo, "1A"))
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-11", deuda_previa=A_NOMBRE)
    assert set(cambio) == CLAVES_DEL_TRASLADO | {"prorrateo"}, f"claves: {sorted(cambio)}"
    assert cambio["trasladado"] == _texto(antes["previo"]), "`trasladado` es sólo la deuda previa, no el prorrateo"
    cuenta = comprobar_el_mes(mundo, "1A", ana, el_prorrateo(cambio), 10, 30, previo=antes["previo"])
    assert cuenta_del_vendedor(cambio) == cuenta, "las dos cosas van a la misma cuenta del vendedor"
    despues = desglose(mundo, "1A")
    assert residuales_anteriores(mundo, "1A") == {} and despues["previo"] == 0, "la deuda previa salió entera"
    parte = D(cambio["prorrateo"]["parte_del_vendedor"])
    assert despues["posterior"] == antes["posterior"] - parte, "del mes salió sólo la parte del vendedor"
    assert despues["deuda"] + deuda_de_cuenta(mundo, cuenta) == deuda_unidad, "la suma de las dos cuentas no cambia"
    claves = [(m["obligacion_id"], m["componente"]) for m in movimientos(mundo, cuenta_de(mundo, "1A"), "traslado")]
    assert len(claves) == len(set(claves)), f"nada se traslada dos veces: {claves}"
    assert cambio["aviso"] == {"deuda": _texto(despues["deuda"])}, cambio["aviso"]


# --- C06: lo ya pagado no se traslada ------------------------------------------------------------------


@pytest.mark.parametrize("pago", ["5000.00", "12000.00"])
def test_c06_sólo_se_traslada_lo_impago_de_la_parte_del_vendedor(mundo: Mundo, pago: str) -> None:
    ana = mundo.personas["ana"]
    mundo_emitido(mundo)
    pagar(mundo, "1A", pago, date(2026, 11, 5))
    comp, antes = del_mes(mundo, "1A"), impago_del_mes(mundo, "1A")
    assert sum(comp[c] - antes[c] for c in COMPONENTES) == D(pago), f"precondición: el pago se imputó al mes: {antes}"
    pagos = movimientos(mundo, cuenta_de(mundo, "1A"), "pago")
    cambio = con_prorrateo(mundo, "1A", [ana], "2026-11-11")
    esperadas = partes_esperadas(mundo, "1A", 10, 30, antes=antes)
    assert total(esperadas) < total(partes_esperadas(mundo, "1A", 10, 30)), "precondición: el pago descuenta algo"
    comprobar_el_mes(mundo, "1A", ana, el_prorrateo(cambio), 10, 30, antes=antes)
    assert movimientos(mundo, cuenta_de(mundo, "1A"), "pago") == pagos, "el pago no se toca"
