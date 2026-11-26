"""H-033 · lo que no tiene que pasar (N01 a N03).

Cada test arma primero el traslado de H-031 y la cuenta de la vendedora; lo que se pide después de ese mundo
(las rutas nuevas) hoy responde 404, que contra el 200, 201, 403 o 422 esperado es una aserción.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from ._h033 import (
    ACCION_DEL_COBRO,
    DIC,
    FECHA_DEL_COBRO,
    HOY,
    Mundo,
    auditorias,
    cobrar,
    cobrar_ok,
    cuenta_aparte,
    cuenta_de,
    cuentas,
    de_la_respuesta,
    del_libro_de_unidades,
    detalle,
    detalle_ok,
    deuda_de_cuenta,
    emitir,
    lista,
    movimientos,
    no_encontrado,
    no_procesable,
    ok,
    pendientes,
    sin_permiso,
    superusuario,
    todo_h033,
    vendedora,
)

SOLO_LEEN = ("contador", "contador_del_edificio", "auxiliar", "consejo")
VECINOS = ("ana", "carla", "beto")
FUERA = ("admin_de_otro_edificio", "consejo_de_otro_edificio", "administracion_b")


def test_n01_sin_el_permiso_da_403_y_no_cambia_nada(mundo: Mundo) -> None:
    """Escenario: Ver pide `ver_morosidad`; cobrar pide `confirmar_pago_informado`"""
    cuenta, _ = vendedora(mundo)
    ok(lista(mundo))  # el administrador sí ve: el 403 de abajo no es una ruta caída
    antes = todo_h033(mundo)
    for rol in VECINOS:
        mundo.como(rol)
        sin_permiso(lista(mundo), "ver_morosidad")
        sin_permiso(detalle(mundo, cuenta), "ver_morosidad")
        sin_permiso(cobrar(mundo, cuenta, "10.00"), "confirmar_pago_informado")
    for rol in SOLO_LEEN:
        mundo.como(rol)
        ok(lista(mundo))
        ok(detalle(mundo, cuenta))
        sin_permiso(cobrar(mundo, cuenta, "10.00"), "confirmar_pago_informado")
    assert todo_h033(mundo) == antes
    mundo.como("admin_del_edificio")
    ok(detalle(mundo, cuenta))
    cobrar_ok(mundo, cuenta, "10.00")


def test_n01_fuera_del_edificio_o_de_la_administracion_da_404(mundo: Mundo) -> None:
    """Escenario: Quien no alcanza el edificio no sabe que la cuenta existe"""
    cuenta, _ = vendedora(mundo)
    ok(lista(mundo))
    antes = todo_h033(mundo)
    for rol in FUERA:
        mundo.como(rol)
        no_encontrado(lista(mundo))
        no_encontrado(detalle(mundo, cuenta))
        no_encontrado(cobrar(mundo, cuenta, "10.00"))
    mundo.como("super_admin")
    no_encontrado(lista(mundo, mundo.edificio_b))  # el edificio de otra administración
    assert todo_h033(mundo) == antes


def test_n01_una_cuenta_de_otro_edificio_de_otra_administracion_o_de_unidad_da_404(mundo: Mundo) -> None:
    """Escenario: La cuenta tiene que ser una cuenta de persona de este edificio"""
    cuenta, _ = vendedora(mundo)
    ok(detalle(mundo, cuenta))
    del_otro = cuenta_aparte(mundo, mundo.admin, mundo.otro, mundo.personas["ana"])
    de_otra_administracion = cuenta_aparte(mundo, mundo.admin_b, mundo.edificio_b, mundo.persona_b)
    # Recongelada (25/11/2026): sólo 1A tiene cuenta en este mundo; antes pedía también la de 1B (IndexError).
    ajenas: list[UUID] = [cuenta_de(mundo, "1A"), del_otro, de_otra_administracion, uuid4()]
    antes = todo_h033(mundo)
    unidades = del_libro_de_unidades(mundo)
    for ajena in ajenas:
        no_encontrado(detalle(mundo, ajena))
        no_encontrado(cobrar(mundo, ajena, "10.00"))
    no_encontrado(detalle(mundo, "no-es-un-uuid"))
    assert todo_h033(mundo) == antes and del_libro_de_unidades(mundo) == unidades
    assert all(f["cuenta_id"] == str(cuenta) for f in cuentas(mundo))  # la lista no suma las ajenas
    assert len(cuentas(mundo)) == 1


@pytest.mark.parametrize("importe", ["0", "0.00", "-1.00", "-0.01", "10.001", "10.505", "abc", "", "1e2", " ", 100,
                                     100.5, None, True])
def test_n02_un_importe_que_no_sirve_da_422_y_no_cambia_nada(mundo: Mundo, importe: Any) -> None:
    """Escenario: Cero, negativo, con más de dos decimales o que no es texto"""
    cuenta, _ = vendedora(mundo)
    cobrar_ok(mundo, cuenta, "10.00")  # la ruta anda: el 422 de abajo es por el importe
    antes = todo_h033(mundo)
    no_procesable(cobrar(mundo, cuenta, importe))
    assert todo_h033(mundo) == antes


@pytest.mark.parametrize("fecha", ["2026-12-16", "2027-01-01", "2026-13-01", "2026-12-32", "15/12/2026", "hoy", "",
                                   None, 20261210])
def test_n02_una_fecha_futura_o_que_no_es_fecha_da_422_y_no_cambia_nada(mundo: Mundo, fecha: Any) -> None:
    """Escenario: La fecha de la transferencia no puede ser posterior a hoy (15/12/2026)"""
    cuenta, _ = vendedora(mundo)
    cobrar_ok(mundo, cuenta, "10.00", HOY.isoformat())  # hoy vale: el 422 de abajo es por la fecha
    antes = todo_h033(mundo)
    no_procesable(cobrar(mundo, cuenta, "10.00", fecha))
    assert todo_h033(mundo) == antes


def test_n02_faltan_campos_da_422(mundo: Mundo) -> None:
    """Escenario: El cuerpo tiene que traer importe y fecha"""
    cuenta, _ = vendedora(mundo)
    cobrar_ok(mundo, cuenta, "10.00")
    antes = todo_h033(mundo)
    ruta = f"/api/complejos/{mundo.edificio}/cuentas-de-vendedores/{cuenta}/cobros"
    for cuerpo in ({}, {"importe": "10.00"}, {"fecha": FECHA_DEL_COBRO}, {"importe": "10.00", "fecha": FECHA_DEL_COBRO,
                                                                         "persona_id": str(uuid4())}):
        no_procesable(mundo.cliente.post(ruta, json=cuerpo))
    assert todo_h033(mundo) == antes


def test_n03_el_cobro_no_toca_unidades_ni_pagos_informados_ni_morosidad(mundo: Mundo) -> None:
    """Escenario: El cobro del vendedor es sólo del vendedor"""
    cuenta, deuda = vendedora(mundo)
    unidades = del_libro_de_unidades(mundo)
    informados = superusuario(mundo, "SELECT count(*) FROM pago_informado WHERE administracion_id = %s",
                              (mundo.admin,))[0][0]
    # Recongelada (25/11/2026): la bandeja es una lista; `ok` la volvía un dict y comparaba [] con {}.
    r_bandeja = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/pagos")
    assert r_bandeja.status_code == 200, r_bandeja.text[:300]
    bandeja = r_bandeja.json()
    morosidad = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/morosidad")
    ok_morosidad = ok(morosidad)
    assert str(cuenta) not in morosidad.text
    cobrar_ok(mundo, cuenta, "1234.56")
    assert deuda_de_cuenta(mundo, cuenta) == deuda - Decimal("1234.56")
    assert del_libro_de_unidades(mundo) == unidades
    assert superusuario(mundo, "SELECT count(*) FROM pago_informado WHERE administracion_id = %s",
                        (mundo.admin,))[0][0] == informados
    assert mundo.cliente.get(f"/api/complejos/{mundo.edificio}/pagos").json() == bandeja
    assert ok(mundo.cliente.get(f"/api/complejos/{mundo.edificio}/morosidad")) == ok_morosidad
    assert len(auditorias(mundo, ACCION_DEL_COBRO)) == 1


def test_n03_el_cobro_no_genera_interes_en_la_cuenta_del_vendedor_al_emitir_el_periodo_siguiente(
        mundo: Mundo) -> None:
    """Escenario: Después de cobrar parte, emitir diciembre no le suma interés a la vendedora"""
    cuenta, deuda = vendedora(mundo)
    cobrar_ok(mundo, cuenta, "1000.00", "2026-12-05")
    antes = pendientes(mundo, cuenta)
    libro = movimientos(mundo, cuenta)
    d_antes = detalle_ok(mundo, cuenta)
    emitir(mundo, DIC, ("1A",))
    assert movimientos(mundo, cuenta) == libro  # ni un movimiento nuevo en su cuenta
    assert pendientes(mundo, cuenta) == antes and deuda_de_cuenta(mundo, cuenta) == deuda - Decimal("1000.00")
    assert detalle_ok(mundo, cuenta) == d_antes and de_la_respuesta(d_antes) == antes
