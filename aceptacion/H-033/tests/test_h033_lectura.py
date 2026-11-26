"""H-033 · C01 y C02: la lista de las cuentas de los vendedores y el detalle de una.

Cada test siembra el traslado de H-031 por su ruta real (que ya anda) y después pide la lectura nueva: hoy esa
ruta no existe y el 404 contra el 200 esperado es la aserción que falla.
"""

from __future__ import annotations

from decimal import Decimal

from ._h033 import (
    CLAVES_DE_LA_CUENTA,
    CLAVES_DEL_DETALLE,
    CLAVES_DEL_MOVIMIENTO,
    ORDEN_R04,
    Mundo,
    cobrar_ok,
    cuenta_del_vendedor,
    cuentas,
    de_la_respuesta,
    detalle_ok,
    deuda_de_cuenta,
    dinero,
    movimientos,
    pendientes,
    sembrar,
    superusuario,
    trasladar,
    vendedora,
)


def test_c01_sin_traslados_la_lista_esta_vacia_y_no_trae_cuentas_de_unidad(mundo: Mundo) -> None:
    """Escenario: Sin vendedores con deuda, la lista del edificio está vacía"""
    sembrar(mundo, ("1A",))
    assert cuentas(mundo) == []


def test_c01_lista_la_cuenta_con_la_persona_la_deuda_y_la_unidad_de_origen(mundo: Mundo) -> None:
    """Escenario: La lista trae a la vendedora con su deuda y la unidad que vendió"""
    cuenta, deuda = vendedora(mundo)
    filas = cuentas(mundo)
    assert len(filas) == 1, filas
    fila = filas[0]
    assert set(fila) == CLAVES_DE_LA_CUENTA, fila
    assert fila["cuenta_id"] == str(cuenta)
    assert fila["persona"] == {"id": str(mundo.personas["ana"]), "nombre": "Ana Prueba"}, fila["persona"]
    assert fila["deuda"] == str(deuda) and fila["deuda"] == f"{deuda:.2f}", (fila["deuda"], deuda)
    assert fila["unidades"] == [{"id": str(mundo.unidades["1A"]), "identificador": "1A"}], fila["unidades"]


def test_c01_ordena_de_mayor_a_menor_deuda_y_junta_las_unidades_de_una_misma_vendedora(mundo: Mundo) -> None:
    """Escenario: Dos vendedoras; la de más deuda primero, aunque se la registró después"""
    sembrar(mundo, ("1A", "1B", "2B"))
    carla = cuenta_del_vendedor(trasladar(mundo, "1B", [mundo.personas["carla"]]))
    ana = cuenta_del_vendedor(trasladar(mundo, "1A", [mundo.personas["ana"]]))
    assert cuenta_del_vendedor(trasladar(mundo, "2B", [mundo.personas["ana"]])) == ana  # una cuenta por persona
    deuda_ana, deuda_carla = deuda_de_cuenta(mundo, ana), deuda_de_cuenta(mundo, carla)
    assert deuda_ana > deuda_carla > 0, (deuda_ana, deuda_carla)
    filas = cuentas(mundo)
    assert [f["cuenta_id"] for f in filas] == [str(ana), str(carla)], filas
    assert [f["deuda"] for f in filas] == [f"{deuda_ana:.2f}", f"{deuda_carla:.2f}"]
    assert [u["identificador"] for u in filas[0]["unidades"]] == ["1A", "2B"], filas[0]["unidades"]
    assert [u["identificador"] for u in filas[1]["unidades"]] == ["1B"], filas[1]["unidades"]


def test_c02_el_detalle_da_el_estado_por_periodo_y_componente_igual_al_libro(mundo: Mundo) -> None:
    """Escenario: El detalle de la cuenta de la vendedora coincide al centavo con el libro"""
    cuenta, deuda = vendedora(mundo)
    d = detalle_ok(mundo, cuenta)
    assert set(d) == CLAVES_DEL_DETALLE, set(d)
    assert d["cuenta_id"] == str(cuenta) and d["persona"] == {"id": str(mundo.personas["ana"]),
                                                             "nombre": "Ana Prueba"}, d
    assert d["deuda"] == f"{deuda:.2f}"
    assert d["unidades"] == [{"id": str(mundo.unidades["1A"]), "identificador": "1A"}], d["unidades"]
    periodos = [p["periodo"] for p in d["periodos"]]
    assert periodos == sorted(periodos) and len(periodos) == len(set(periodos)) and len(periodos) >= 2, periodos
    assert de_la_respuesta(d) == pendientes(mundo, cuenta)
    assert sum(de_la_respuesta(d).values(), Decimal("0.00")) == deuda
    for p in d["periodos"]:
        assert list(p["componentes"]) == sorted(p["componentes"], key=ORDEN_R04.index), p
        for valores in p["componentes"].values():
            assert set(valores) == {"debe", "cobrado", "pendiente"}, valores
            assert dinero(valores["debe"]) - dinero(valores["cobrado"]) == dinero(valores["pendiente"]), valores
            assert dinero(valores["debe"]) > 0 and dinero(valores["cobrado"]) == 0, valores  # nadie cobró todavía


def test_c02_el_detalle_lista_los_traslados_y_los_cobros_en_orden(mundo: Mundo) -> None:
    """Escenario: Los movimientos del detalle son los del libro, en el orden en que se registraron"""
    cuenta, deuda = vendedora(mundo)
    antes = detalle_ok(mundo, cuenta)["movimientos"]
    libro = movimientos(mundo, cuenta)
    assert len(antes) == len(libro) >= 2 and all(x["tipo"] == "traslado" for x in antes), antes
    cobrar_ok(mundo, cuenta, "1000.00", "2026-12-05")
    cobrar_ok(mundo, cuenta, "250.50", "2026-12-10")
    d = detalle_ok(mundo, cuenta)
    libro = movimientos(mundo, cuenta)
    fechas = {str(f[0]): f[1].isoformat() for f in superusuario(
        mundo, "SELECT id, fecha_valor FROM movimiento WHERE cuenta_id = %s", (cuenta,))}
    assert [x["id"] for x in d["movimientos"]] == [str(x["id"]) for x in libro], d["movimientos"]
    assert all(set(x) == CLAVES_DEL_MOVIMIENTO for x in d["movimientos"]), d["movimientos"]
    assert [(x["tipo"], x["sentido"], x["importe"], x["fecha"]) for x in d["movimientos"]] == [
        (x["tipo"], x["sentido"], f"{x['importe']:.2f}", fechas[str(x["id"])]) for x in libro]
    assert [x["tipo"] for x in d["movimientos"]][-2:] == ["pago", "pago"]
    assert [x["sentido"] for x in d["movimientos"]][-2:] == ["credito", "credito"]
    assert [x["importe"] for x in d["movimientos"]][-2:] == ["1000.00", "250.50"]
    assert [x["fecha"] for x in d["movimientos"]][-2:] == ["2026-12-05", "2026-12-10"]
    debitos = sum((dinero(x["importe"]) for x in d["movimientos"] if x["sentido"] == "debito"), Decimal("0.00"))
    assert debitos == deuda, (debitos, deuda)
    assert d["deuda"] == f"{deuda - Decimal('1250.50'):.2f}"
