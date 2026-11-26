"""H-033 · C03 a C05: registrar el cobro de la vendedora, imputarlo con R04, cerrarla en cero y auditarlo.

Todos arman el traslado de H-031 (que ya anda) y cobran por la ruta nueva: hoy da 404 y el test falla por la
aserción del 201. La imputación se compara con R04 escrito aparte (`r04`), no con el código de producción.
"""

from __future__ import annotations

from decimal import Decimal

from ._h033 import (
    ACCION_DEL_COBRO,
    FECHA_DEL_COBRO,
    HOY,
    ORDEN_R04,
    Mundo,
    auditorias,
    cobrar,
    cobrar_ok,
    cuentas,
    de_la_respuesta,
    detalle_ok,
    deuda_de_cuenta,
    movimientos,
    no_procesable,
    pendientes,
    r04,
    superusuario,
    todo_h033,
    vendedora,
)

CENTAVO = Decimal("0.01")


def _por_r04(antes: dict[tuple[str, str], Decimal]) -> list[tuple[str, str]]:
    return sorted(antes, key=lambda k: (k[0], ORDEN_R04.index(k[1])))


def test_c03_responde_201_con_el_estado_actualizado_y_la_deuda_baja_exactamente_el_importe(mundo: Mundo) -> None:
    """Escenario: Cobrarle una parte a la vendedora"""
    cuenta, deuda = vendedora(mundo)
    antes = len(movimientos(mundo, cuenta))
    d = cobrar_ok(mundo, cuenta, "1000.00", FECHA_DEL_COBRO)
    assert d["deuda"] == f"{deuda - Decimal('1000.00'):.2f}", d["deuda"]
    assert d == detalle_ok(mundo, cuenta)  # lo que responde el POST es lo que lee el GET
    assert deuda_de_cuenta(mundo, cuenta) == deuda - Decimal("1000.00")
    nuevos = movimientos(mundo, cuenta)[antes:]
    assert len(nuevos) == 1, nuevos
    assert (nuevos[0]["tipo"], nuevos[0]["sentido"], nuevos[0]["importe"]) == ("pago", "credito", Decimal("1000.00"))
    assert nuevos[0]["operacion_id"] is not None
    fecha, por = superusuario(mundo, "SELECT fecha_valor, registrado_por FROM movimiento WHERE id = %s",
                              (nuevos[0]["id"],))[0]
    assert fecha.isoformat() == FECHA_DEL_COBRO and str(por) == str(mundo.personas["admin_principal"])
    assert [f["deuda"] for f in cuentas(mundo)] == [d["deuda"]]


def test_c03_el_cobro_se_imputa_con_r04_al_centavo_cobro_tras_cobro(mundo: Mundo) -> None:
    """Escenario: Cobros parciales que cruzan períodos y componentes siguen el orden de R04"""
    cuenta, deuda = vendedora(mundo)
    claves = _por_r04(pendientes(mundo, cuenta))
    assert len(claves) >= 3, f"precondición: al menos tres (período, componente) con deuda: {claves}"
    antes = pendientes(mundo, cuenta)
    primero = antes[claves[0]] + antes[claves[1]] - CENTAVO  # termina un centavo antes de cerrar el segundo
    d1 = cobrar_ok(mundo, cuenta, f"{primero:.2f}", "2026-12-05")
    esperado = r04(antes, primero)
    assert pendientes(mundo, cuenta) == esperado, (pendientes(mundo, cuenta), esperado)
    assert de_la_respuesta(d1) == esperado
    assert esperado[claves[1]] == CENTAVO and claves[0] not in esperado
    segundo = (sum(esperado.values(), Decimal("0.00")) / 2).quantize(CENTAVO)
    d2 = cobrar_ok(mundo, cuenta, f"{segundo:.2f}", "2026-12-10")
    esperado2 = r04(esperado, segundo)
    assert pendientes(mundo, cuenta) == esperado2 and de_la_respuesta(d2) == esperado2
    assert deuda_de_cuenta(mundo, cuenta) == deuda - primero - segundo
    imputado = superusuario(mundo, "SELECT coalesce(sum(i.importe), 0) FROM imputacion i JOIN movimiento m "
                                   "ON m.id = i.movimiento_id WHERE m.cuenta_id = %s AND m.tipo = 'pago'",
                            (cuenta,))[0][0]
    assert imputado == primero + segundo, (imputado, primero, segundo)  # nada quedó a favor: se imputó todo


def test_c03_la_fecha_es_la_de_la_transferencia_y_puede_ser_anterior_a_hoy(mundo: Mundo) -> None:
    """Escenario: El cobro se fecha el día de la transferencia, que puede ser de antes; hoy también vale"""
    cuenta, _ = vendedora(mundo)
    cobrar_ok(mundo, cuenta, "100.00", "2026-11-20")
    cobrar_ok(mundo, cuenta, "100.00", HOY.isoformat())
    d = detalle_ok(mundo, cuenta)
    assert [(x["tipo"], x["fecha"]) for x in d["movimientos"]][-2:] == [("pago", "2026-11-20"),
                                                                        ("pago", HOY.isoformat())]


def test_c04_un_cobro_igual_a_la_deuda_deja_la_cuenta_en_cero(mundo: Mundo) -> None:
    """Escenario: Cobrar el resto deja a la vendedora en cero"""
    cuenta, deuda = vendedora(mundo)
    cobrar_ok(mundo, cuenta, f"{deuda / 3:.2f}")
    resto = deuda_de_cuenta(mundo, cuenta)
    d = cobrar_ok(mundo, cuenta, f"{resto:.2f}")
    assert d["deuda"] == "0.00" and deuda_de_cuenta(mundo, cuenta) == 0
    assert pendientes(mundo, cuenta) == {} and de_la_respuesta(d) == {}
    assert [(f["cuenta_id"], f["deuda"]) for f in cuentas(mundo)] == [(str(cuenta), "0.00")]  # sigue en la lista
    assert detalle_ok(mundo, cuenta)["deuda"] == "0.00"
    antes = todo_h033(mundo)
    no_procesable(cobrar(mundo, cuenta, "0.01"))  # ya no debe nada
    assert todo_h033(mundo) == antes


def test_c04_un_cobro_mayor_que_la_deuda_da_422_y_no_cambia_nada(mundo: Mundo) -> None:
    """Escenario: Cobrar un centavo de más se rechaza entero, sin crédito a favor"""
    cuenta, deuda = vendedora(mundo)
    cobrar_ok(mundo, cuenta, "500.00")
    resto = deuda_de_cuenta(mundo, cuenta)
    assert resto == deuda - Decimal("500.00")
    antes = todo_h033(mundo)
    for importe in (f"{resto + CENTAVO:.2f}", f"{resto * 2:.2f}", "999999999.00"):
        no_procesable(cobrar(mundo, cuenta, importe))
    assert todo_h033(mundo) == antes
    assert deuda_de_cuenta(mundo, cuenta) == resto
    cobrar_ok(mundo, cuenta, f"{resto:.2f}")  # el pedido corregido sí entra
    assert deuda_de_cuenta(mundo, cuenta) == 0


def test_c05_cada_cobro_queda_auditado_con_cuenta_importe_y_fecha(mundo: Mundo) -> None:
    """Escenario: La auditoría registra cada cobro, de quien lo hizo"""
    cuenta, _ = vendedora(mundo)
    assert auditorias(mundo, ACCION_DEL_COBRO) == []
    cobrar_ok(mundo, cuenta, "1000.00", "2026-12-05")
    mundo.como("admin_del_edificio")  # el administrador del edificio también cobra
    cobrar_ok(mundo, cuenta, "250.50", "2026-12-10")
    filas = sorted(auditorias(mundo, ACCION_DEL_COBRO), key=lambda f: f[3]["fecha"])
    assert len(filas) == 2, filas
    for (entidad, entidad_id, persona_id, detalle), (importe, fecha, quien) in zip(
            filas, (("1000.00", "2026-12-05", "admin_principal"), ("250.50", "2026-12-10", "admin_del_edificio")),
            strict=True):
        assert (entidad, str(entidad_id), str(persona_id)) == ("cuenta", str(cuenta), str(mundo.personas[quien]))
        assert detalle == {"cuenta_id": str(cuenta), "importe": importe, "fecha": fecha}, detalle
