"""Aceptación de H-031: la deuda previa a nombre del vendedor (change 4d `cambio-de-titular`, CRITICAL; R32, D-168.2).

Cada test lleva su criterio en el nombre (C01…, N01…). Los montos se verifican contra el libro
(`estado_de_cuenta` de las dos cuentas y la tabla `movimiento`), no sólo contra la respuesta. Hoy la ruta de H-030
contesta 422 a `deuda_previa: "a_nombre_del_vendedor"`: cada test falla por aserción (el 201 que espera).
"""

from __future__ import annotations

import re
from datetime import date
from uuid import UUID, uuid4

import pytest

from ._h031 import (
    A_NOMBRE,
    CLAVES_DEL_TRASLADO,
    DIC,
    EMAIL_DE_ANA,
    FECHA,
    HOY,
    NOV,
    OCT,
    SEP,
    Mundo,
    asignaciones,
    cuenta_de,
    cuenta_del_vendedor,
    cuentas_de_persona,
    del_libro,
    deuda_de_cuenta,
    desglose,
    dinero,
    emitir,
    estado,
    movimientos,
    no_procesable,
    pagar,
    periodos_de_obligaciones,
    registrar,
    residuales_anteriores,
    sembrar,
    superusuario,
    todo,
    trasladar,
    traslados,
)

MONTO = re.compile(r"^[0-9]+\.[0-9]{2}$")


def _texto(valor: object) -> str:
    return format(valor, ".2f")


# --- C01: la opción y la respuesta ---------------------------------------------------------------------


def test_c01_responde_201_con_trasladado_y_la_cuenta_del_vendedor(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    previo = sembrar(mundo)["previo"]
    cambio = trasladar(mundo, "1A", [ana], ana)
    assert set(cambio) == CLAVES_DEL_TRASLADO, f"claves de la respuesta: {sorted(cambio)}"
    assert cambio["deuda_previa"] == A_NOMBRE and cambio["expensa_del_mes"] == "entera", cambio
    assert isinstance(cambio["trasladado"], str) and MONTO.match(cambio["trasladado"]), cambio
    assert cambio["trasladado"] == _texto(previo), f"trasladado {cambio['trasladado']} contra el libro {previo}"
    assert cuenta_del_vendedor(cambio) in cuentas_de_persona(mundo, ana), "la cuenta es de persona, la de Ana"
    guardada = superusuario(mundo, "SELECT deuda_previa FROM cambio_de_titular WHERE id = %s", (cambio["id"],))
    assert guardada == [(A_NOMBRE,)], f"el cambio guarda la opción elegida: {guardada}"


def test_c01_con_un_solo_vendedor_puede_omitir_al_deudor(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    previo = sembrar(mundo)["previo"]
    cambio = trasladar(mundo, "1A", [ana])
    assert cambio["trasladado"] == _texto(previo), cambio
    assert cuenta_del_vendedor(cambio) in cuentas_de_persona(mundo, ana), cambio


def test_c01_con_dos_vendedores_la_deuda_queda_a_nombre_del_elegido(mundo: Mundo) -> None:
    dora, edu = mundo.personas["dora"], mundo.personas["edu"]
    previo = sembrar(mundo, ("2A",))["previo"]
    cambio = trasladar(mundo, "2A", [dora, edu], edu)
    assert cuentas_de_persona(mundo, dora) == [], "Dora no es la deudora: no tiene cuenta"
    assert cuenta_del_vendedor(cambio) in cuentas_de_persona(mundo, edu), cambio
    assert deuda_de_cuenta(mundo, cuenta_del_vendedor(cambio)) == previo, "Edu debe lo trasladado"


def test_c01_el_aviso_dice_lo_que_le_queda_a_la_unidad(mundo: Mundo) -> None:
    posterior = sembrar(mundo)["posterior"]
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]])
    assert cambio["aviso"] == {"deuda": _texto(posterior)}, f"el aviso es la deuda que queda en la unidad: {cambio}"


# --- C02: la unidad en cero por lo anterior, el vendedor debe lo mismo --------------------------------


@pytest.mark.parametrize("fecha", ["2026-11-01", "2026-11-10", "2026-11-30"])
def test_c02_lo_anterior_al_mes_del_cambio_pasa_entero_al_vendedor(mundo: Mundo, fecha: str) -> None:
    antes = sembrar(mundo)
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]], fecha=fecha)
    despues = desglose(mundo, "1A")
    assert residuales_anteriores(mundo, "1A") == {}, "ningún componente anterior a noviembre queda impago"
    assert despues["previo"] == 0 and despues["posterior"] == antes["posterior"], (antes, despues)
    vendedor = deuda_de_cuenta(mundo, cuenta_del_vendedor(cambio))
    assert vendedor == antes["previo"], f"el vendedor debe {vendedor}, la unidad debía {antes['previo']}"
    assert cambio["trasladado"] == _texto(antes["previo"]), cambio
    assert despues["deuda"] + vendedor == antes["deuda"], "la suma de las dos cuentas no cambia"


def test_c02_con_fecha_de_octubre_sólo_pasa_septiembre(mundo: Mundo) -> None:
    sembrar(mundo)
    antes = desglose(mundo, "1A", OCT)
    assert antes["previo"] > 0, f"precondición: septiembre debe algo: {antes}"
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]], fecha="2026-10-20")
    despues = desglose(mundo, "1A", OCT)
    assert despues["previo"] == 0 and despues["posterior"] == antes["posterior"], (antes, despues)
    assert deuda_de_cuenta(mundo, cuenta_del_vendedor(cambio)) == antes["previo"] == dinero(cambio["trasladado"])


def test_c02_el_interes_registrado_se_traslada_con_el_capital(mundo: Mundo) -> None:
    antes = sembrar(mundo)
    intereses = {k: v for k, v in residuales_anteriores(mundo, "1A").items() if k[1] == "interes"}
    assert sum(intereses.values()) == antes["previo_interes"] > 0, f"precondición: {intereses}"
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]])
    assert {k for k in residuales_anteriores(mundo, "1A") if k[1] == "interes"} == set(), "interés en cero"
    capital = antes["previo"] - antes["previo_interes"]
    assert dinero(cambio["trasladado"]) == capital + antes["previo_interes"], cambio
    assert deuda_de_cuenta(mundo, cuenta_del_vendedor(cambio)) == capital + antes["previo_interes"]


# --- C03: los movimientos `traslado` -------------------------------------------------------------------


def test_c03_un_credito_en_la_unidad_por_obligacion_y_su_debito_enlazado_en_el_vendedor(mundo: Mundo) -> None:
    sembrar(mundo)
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]])
    unidad, vendedor = cuenta_de(mundo, "1A"), cuenta_del_vendedor(cambio)
    creditos, debitos = movimientos(mundo, unidad, "traslado"), movimientos(mundo, vendedor, "traslado")
    assert creditos and debitos, f"hay traslados en las dos cuentas: {len(creditos)} y {len(debitos)}"
    assert {c["sentido"] for c in creditos} == {"credito"} and {d["sentido"] for d in debitos} == {"debito"}
    periodos = periodos_de_obligaciones(mundo, unidad)
    assert {periodos[UUID(str(c["obligacion_id"]))] for c in creditos} == {SEP, OCT}, "un crédito por obligación"
    total = dinero(cambio["trasladado"])
    assert sum(dinero(c["importe"]) for c in creditos) == total == sum(dinero(d["importe"]) for d in debitos)
    assert len(traslados(mundo)) == len(creditos) + len(debitos), "no hay más traslados que los de este cambio"
    usados: set[UUID] = set()
    for c in creditos:
        pares = [d for d in debitos if d["enlazado_a"] == c["id"] or c["enlazado_a"] == d["id"]]
        assert len(pares) == 1, f"cada crédito tiene un solo débito enlazado: {c}"
        assert dinero(pares[0]["importe"]) == dinero(c["importe"]), "la contraparte es del mismo importe"
        assert pares[0]["id"] not in usados, "un débito no sirve a dos créditos"
        usados.add(pares[0]["id"])
    assert usados == {d["id"] for d in debitos}, "ningún débito queda suelto"
    assert all(m["operacion_id"] is not None for m in [*creditos, *debitos]), "cada traslado trae su operacion_id"


# --- C04: lo pagado y lo posterior no se mueven --------------------------------------------------------


@pytest.mark.parametrize("fecha", [FECHA, "2026-10-20"])
def test_c04_lo_ya_pagado_no_se_mueve(mundo: Mundo, fecha: str) -> None:
    sembrar(mundo)
    unidad = cuenta_de(mundo, "1A")
    consulta = ("SELECT count(*), coalesce(md5(string_agg(i::text, '|' ORDER BY i::text)), '') FROM imputacion i "
                "WHERE i.movimiento_id IN (SELECT id FROM movimiento WHERE cuenta_id = %s AND tipo = 'pago')")
    pagos = movimientos(mundo, unidad, "pago")
    imputaciones = superusuario(mundo, consulta, (unidad,))
    assert pagos and imputaciones[0][0] > 0, "precondición: hay un pago parcial con sus imputaciones"
    trasladar(mundo, "1A", [mundo.personas["ana"]], fecha=fecha)
    assert movimientos(mundo, unidad, "pago") == pagos, "los pagos de la unidad quedan como estaban"
    assert superusuario(mundo, consulta, (unidad,)) == imputaciones, "y sus imputaciones también"


def test_c04_la_deuda_del_mes_del_cambio_y_de_los_posteriores_queda_en_la_unidad(mundo: Mundo) -> None:
    sembrar(mundo)
    emitir(mundo, DIC, ("1A",), {"1A": "10000.00"})
    antes = desglose(mundo, "1A")
    assert antes["posterior"] > 10000, f"precondición: noviembre y diciembre deben: {antes}"
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]])
    despues = desglose(mundo, "1A")
    assert despues["posterior"] == antes["posterior"] and despues["previo"] == 0, (antes, despues)
    assert dinero(cambio["trasladado"]) == antes["previo"], cambio


# --- C05: el interés después del traslado --------------------------------------------------------------


def test_c05_emitir_el_mes_siguiente_no_da_interes_sobre_lo_trasladado(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    sembrar(mundo, ("1A", "2B"), parcial=False)
    cambio = trasladar(mundo, "1A", [ana])
    vendedor = cuenta_del_vendedor(cambio)
    antes_vendedor = deuda_de_cuenta(mundo, vendedor)
    uno, dos = cuenta_de(mundo, "1A"), cuenta_de(mundo, "2B")
    previos = {m["id"] for m in movimientos(mundo, uno, "interes")} | {m["id"] for m in
                                                                      movimientos(mundo, dos, "interes")}
    emitir(mundo, DIC, ("1A", "2B"), {"1A": "10000.00", "2B": "10000.00"})

    def nuevos(cuenta: UUID) -> dict[UUID, date]:
        periodo = periodos_de_obligaciones(mundo, cuenta)
        return {m["id"]: periodo[UUID(str(m["obligacion_id"]))] for m in movimientos(mundo, cuenta, "interes")
                if m["id"] not in previos}

    en_la_unidad, en_el_control = nuevos(uno), nuevos(dos)
    assert en_la_unidad, "la unidad sigue generando interés sobre lo que le quedó (noviembre)"
    assert all(p >= NOV for p in en_la_unidad.values()), f"interés sobre lo trasladado: {en_la_unidad}"
    assert any(p < NOV for p in en_el_control.values()), "el control sí genera interés sobre septiembre u octubre"
    suma = sum(dinero(m["importe"]) for m in movimientos(mundo, uno, "interes") if m["id"] in en_la_unidad)
    control = sum(dinero(m["importe"]) for m in movimientos(mundo, dos, "interes")
                  if en_el_control.get(m["id"]) == NOV)
    assert suma == control > 0, f"interés de noviembre: unidad {suma}, control sin traslado {control}"
    assert movimientos(mundo, vendedor, "interes") == [], "la cuenta del vendedor no genera interés"
    assert deuda_de_cuenta(mundo, vendedor) == antes_vendedor, "la deuda del vendedor no crece"


# --- C06: la cuenta de persona -------------------------------------------------------------------------


def test_c06_se_crea_la_cuenta_del_vendedor_y_se_reutiliza_en_el_edificio(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    sembrar(mundo, ("1A", "2B"), parcial=False)
    assert cuentas_de_persona(mundo, ana) == [], "precondición: Ana no tiene cuenta de persona"
    primero = trasladar(mundo, "1A", [ana])
    cuenta = cuenta_del_vendedor(primero)
    assert cuentas_de_persona(mundo, ana) == [cuenta], "se crea una cuenta de persona"
    antes = deuda_de_cuenta(mundo, cuenta)
    previo_2b = desglose(mundo, "2B")["previo"]
    segundo = trasladar(mundo, "2B", [ana], compradores=[{"nombre": "Omar Comprador", "email": None}])
    assert cuenta_del_vendedor(segundo) == cuenta, "la segunda deuda va a la misma cuenta"
    assert cuentas_de_persona(mundo, ana) == [cuenta], "no se crea una cuenta nueva (uq_cuenta_persona)"
    assert deuda_de_cuenta(mundo, cuenta) == antes + previo_2b == antes + dinero(segundo["trasladado"])


# --- C07: sin deuda previa -----------------------------------------------------------------------------


def test_c07_sin_nada_emitido_se_registra_igual_sin_movimientos(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    libro = del_libro(mundo)
    cambio = trasladar(mundo, "1A", [ana])
    assert cambio["trasladado"] == "0.00", cambio
    assert cambio["cuenta_del_vendedor"] is None, "sin deuda no se crea cuenta ni se devuelve"
    assert del_libro(mundo) == libro, "el libro queda idéntico"
    assert cuentas_de_persona(mundo, ana) == []
    assert ana not in {UUID(str(f[0])) for f in superusuario(
        mundo, "SELECT persona_id FROM asignacion_rol WHERE unidad_id = %s AND vinculo = 'propietario'",
        (mundo.unidades["1A"],))}, "el cambio se registró: Ana ya no es propietaria"
    assert superusuario(mundo, "SELECT deuda_previa FROM cambio_de_titular WHERE id = %s",
                        (cambio["id"],)) == [(A_NOMBRE,)]


def test_c07_con_todo_lo_anterior_pagado_tampoco_hay_traslado(mundo: Mundo) -> None:
    importes = {"1A": "10000.00"}
    emitir(mundo, SEP, ("1A",), importes)
    pagar(mundo, "1A", "10000.00", date(2026, 9, 5))
    emitir(mundo, OCT, ("1A",), importes)
    pagar(mundo, "1A", "10000.00", date(2026, 10, 5))
    emitir(mundo, NOV, ("1A",), importes)
    assert desglose(mundo, "1A")["previo"] == 0, "precondición: nada anterior a noviembre"
    libro = del_libro(mundo)
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]])
    assert cambio["trasladado"] == "0.00" and cambio["cuenta_del_vendedor"] is None, cambio
    assert del_libro(mundo) == libro and traslados(mundo) == [], "sin movimientos ni cuentas nuevas"


# --- N01: el vendedor deudor ---------------------------------------------------------------------------


@pytest.mark.parametrize("deudor", ["carla", "inexistente"])
def test_n01_un_deudor_que_no_es_vendedor_da_422_y_nada_cambia(mundo: Mundo, deudor: str) -> None:
    ana = mundo.personas["ana"]
    previo = sembrar(mundo)["previo"]
    antes = todo(mundo)
    ajeno = mundo.personas["carla"] if deudor == "carla" else uuid4()
    r = registrar(mundo, "1A", [ana], deuda_previa=A_NOMBRE, vendedor_deudor=str(ajeno))
    no_procesable(r)
    assert todo(mundo) == antes, "el 422 no cambia nada"
    cambio = trasladar(mundo, "1A", [ana], ana)
    assert cambio["trasladado"] == _texto(previo), "y el pedido bueno traslada todo, una vez"


def test_n01_con_mas_de_un_vendedor_falta_el_deudor(mundo: Mundo) -> None:
    dora, edu = mundo.personas["dora"], mundo.personas["edu"]
    previo = sembrar(mundo, ("2A",))["previo"]
    antes = todo(mundo)
    no_procesable(registrar(mundo, "2A", [dora, edu], deuda_previa=A_NOMBRE))
    assert todo(mundo) == antes, "el 422 no cambia nada"
    cambio = trasladar(mundo, "2A", [dora, edu], dora)
    assert cambio["trasladado"] == _texto(previo), cambio


# --- N02: un pedido que falla no deja rastro -----------------------------------------------------------


@pytest.mark.parametrize("falla", ["sin_compradores", "fecha_futura", "comprador_es_el_vendedor"])
def test_n02_un_pedido_que_falla_no_deja_movimientos_ni_cuenta_ni_fila_ni_auditoria(mundo: Mundo,
                                                                                      falla: str) -> None:
    ana = mundo.personas["ana"]
    previo = sembrar(mundo)["previo"]
    antes = todo(mundo)
    if falla == "sin_compradores":
        r = registrar(mundo, "1A", [ana], [], deuda_previa=A_NOMBRE, vendedor_deudor=str(ana))
    elif falla == "fecha_futura":
        r = registrar(mundo, "1A", [ana], fecha="2026-12-20", deuda_previa=A_NOMBRE, vendedor_deudor=str(ana))
    else:
        r = registrar(mundo, "1A", [ana], [{"nombre": "Ana Prueba", "email": EMAIL_DE_ANA}],
                      deuda_previa=A_NOMBRE, vendedor_deudor=str(ana))
    no_procesable(r)
    assert todo(mundo) == antes, "ni movimientos, ni cuenta, ni fila, ni auditoría, ni asignaciones"
    assert cuentas_de_persona(mundo, ana) == [] and traslados(mundo) == []
    cambio = trasladar(mundo, "1A", [ana], ana)
    assert cambio["trasladado"] == _texto(previo), "el pedido bueno después traslada todo, una sola vez"
    assert len(cuentas_de_persona(mundo, ana)) == 1


# --- N03: la cuenta del vendedor fuera de la cobranza --------------------------------------------------


def test_n03_la_cuenta_del_vendedor_no_aparece_en_la_morosidad_ni_en_la_situacion(mundo: Mundo) -> None:
    from proptech_core.cuenta_corriente.aplicacion import cobranza

    from ._h031 import sesion_app

    sembrar(mundo, ("1A",), parcial=False)
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]], compradores=[
        {"nombre": "Nora Compradora", "email": None}])
    vendedor = cuenta_del_vendedor(cambio)
    r = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/morosidad")
    assert r.status_code == 200, f"morosidad: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    assert [f["unidad"] for f in cuerpo["unidades"]] == ["1A"], f"sólo la unidad: {cuerpo['unidades']}"
    fila = cuerpo["unidades"][0]
    assert fila["propietarios"] == ["Nora Compradora"] and fila["capital"] == "10000.00", fila
    assert cuerpo["resumen"]["unidades_con_deuda"] == 1 and cuerpo["resumen"]["total_vencido"] == fila[
        "total_vencido"], "la deuda del vendedor no suma al total"
    with sesion_app(mundo.base, mundo.admin) as s:
        situaciones = cobranza.situacion_del_edificio(s, complejo_id=mundo.edificio, fecha=HOY)
    cuentas = {UUID(str(x.cuenta_id)) for x in situaciones}
    assert vendedor not in cuentas, "la cuenta de persona no tiene situación de cobranza"
    assert cuenta_de(mundo, "1A") in cuentas and cuentas == {cuenta_de(mundo, u) for u in
                                                              ("1A", "1B", "2A", "2B")}, cuentas


# --- N04: un pago posterior no toca lo trasladado ------------------------------------------------------


def test_n04_un_pago_posterior_sobre_la_unidad_no_se_imputa_a_la_deuda_trasladada(mundo: Mundo) -> None:
    sembrar(mundo, ("1A",), parcial=False)
    cambio = trasladar(mundo, "1A", [mundo.personas["ana"]])
    vendedor = cuenta_del_vendedor(cambio)
    trasladada = deuda_de_cuenta(mundo, vendedor)
    posterior = desglose(mundo, "1A")["posterior"]
    pagar(mundo, "1A", "1000.00", date(2026, 11, 25))
    assert deuda_de_cuenta(mundo, vendedor) == trasladada, "el pago no baja lo que debe el vendedor"
    assert desglose(mundo, "1A")["posterior"] == posterior - 1000, "el pago baja lo que quedó en la unidad"
    assert superusuario(mundo, "SELECT count(*) FROM imputacion WHERE cuenta_id = %s", (vendedor,))[0][0] == 0
    pagar(mundo, "1A", _texto(posterior - 1000 + 500), date(2026, 11, 26))
    assert deuda_de_cuenta(mundo, vendedor) == trasladada, "pagar de más tampoco paga lo trasladado"
    e = estado(mundo, cuenta_de(mundo, "1A"))
    assert e.deuda.a_texto() == "0.00" and e.credito_a_favor.a_texto() == "500.00", (
        f"el exceso queda a favor de la unidad: deuda {e.deuda.a_texto()}, a favor {e.credito_a_favor.a_texto()}")


# --- N05: un segundo cambio no vuelve a trasladar ------------------------------------------------------


def test_n05_un_segundo_cambio_traslada_sólo_lo_que_no_se_había_trasladado(mundo: Mundo) -> None:
    ana = mundo.personas["ana"]
    inicial = sembrar(mundo, ("1A",), parcial=False)
    uno = trasladar(mundo, "1A", [ana], compradores=[{"nombre": "Nora Compradora", "email": None}])
    nora = UUID(uno["compradores"][0]["persona_id"])
    unidad, cuenta_ana = cuenta_de(mundo, "1A"), cuenta_del_vendedor(uno)
    traslados_de_ana = traslados(mundo)
    noviembre = desglose(mundo, "1A", DIC)["previo"]
    assert noviembre > 0, "precondición: queda noviembre"
    dos = trasladar(mundo, "1A", [nora], compradores=[{"nombre": "Omar Comprador", "email": None}],
                    fecha="2026-12-10")
    assert dos["trasladado"] == _texto(noviembre), f"sólo noviembre, no septiembre y octubre otra vez: {dos}"
    cuenta_nora = cuenta_del_vendedor(dos)
    assert cuenta_nora != cuenta_ana and cuenta_nora in cuentas_de_persona(mundo, nora)
    assert deuda_de_cuenta(mundo, cuenta_ana) == dinero(uno["trasladado"]), "la deuda de Ana no se toca"
    assert deuda_de_cuenta(mundo, cuenta_nora) == noviembre
    assert desglose(mundo, "1A", DIC)["deuda"] == 0
    assert deuda_de_cuenta(mundo, cuenta_ana) + deuda_de_cuenta(mundo, cuenta_nora) == inicial["deuda"]
    en_septiembre_y_octubre = [t for t in traslados(mundo) if t[1] == unidad and t[2] == "credito"
                               and periodos_de_obligaciones(mundo, unidad)[UUID(str(t[4]))] < NOV]
    assert len(en_septiembre_y_octubre) == len([t for t in traslados_de_ana if t[1] == unidad]), (
        "septiembre y octubre se trasladaron una sola vez")


def test_n05_un_segundo_cambio_del_mismo_mes_no_traslada_nada(mundo: Mundo) -> None:
    sembrar(mundo, ("1A",), parcial=False)
    uno = trasladar(mundo, "1A", [mundo.personas["ana"]], compradores=[
        {"nombre": "Nora Compradora", "email": None}])
    nora = UUID(uno["compradores"][0]["persona_id"])
    libro = del_libro(mundo)
    dos = trasladar(mundo, "1A", [nora], compradores=[{"nombre": "Omar Comprador", "email": None}],
                    fecha="2026-11-20")
    assert dos["trasladado"] == "0.00" and dos["cuenta_del_vendedor"] is None, dos
    assert del_libro(mundo) == libro, "lo anterior a noviembre ya estaba en cero: el libro no cambia"
    assert asignaciones(mundo) != [], "el cambio se registró igual"
