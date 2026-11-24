"""Aceptación de H-027: la lectura de la morosidad (change 10a `morosidad`, HIGH; HU-A8, R20, R30, D-167).

Cada test lleva su criterio en el nombre (C01…, N01…) y el escenario de la spec que cubre en su docstring.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest

from ._h027 import (
    CLAVES_DE_FILA,
    EMAIL_DE_ANA,
    HOY,
    MENSUAL,
    NOV,
    OCT,
    SEP,
    Mundo,
    anular,
    armar_la_base,
    del_libro,
    emitir,
    filas,
    intereses_registrados,
    morosidad,
    no_encontrado,
    pagar,
    pedir,
    sin_permiso,
    situacion_del_libro,
)

MONTO = re.compile(r"^-?[0-9]+\.[0-9]{2}$")


def test_c01_cada_fila_trae_lo_que_pide_hu_a8(mundo: Mundo) -> None:
    """Escenario: Moroso crítico y unidad al día"""
    armar_la_base(mundo)
    cuerpo = morosidad(mundo)
    assert cuerpo["fecha"] == "2026-11-18", cuerpo["fecha"]
    assert cuerpo["intereses_al"] == "2026-10-31", f"el último corte de interés es el 31/10: {cuerpo['intereses_al']}"
    por_unidad = {f["unidad"]: f for f in cuerpo["unidades"]}
    assert set(por_unidad) == {"1A", "1B", "2A", "2B"}, por_unidad.keys()
    for fila in cuerpo["unidades"]:
        assert set(fila) == CLAVES_DE_FILA, f"claves de la fila de {fila.get('unidad')}: {sorted(fila)}"
        for clave in ("total_vencido", "capital", "intereses"):
            assert isinstance(fila[clave], str) and MONTO.match(fila[clave]), f"{clave} como texto: {fila}"
        assert Decimal(fila["capital"]) + Decimal(fila["intereses"]) == Decimal(fila["total_vencido"]), fila
        assert fila["unidad_id"] == str(mundo.unidades[fila["unidad"]]), fila
    a = por_unidad["1A"]
    interes = intereses_registrados(mundo, "1A")
    assert interes > 0, "precondición: `1A` tiene interés registrado de septiembre y octubre"
    assert a["capital"] == "30000.00", a
    assert a["intereses"] == f"{interes:.2f}", f"los intereses de `1A` son los registrados ({interes}): {a}"
    assert a["total_vencido"] == f"{Decimal('30000.00') + interes:.2f}", a
    assert a["liquidaciones_vencidas"] == 3, a
    assert a["vencida_desde"] == "2026-09-10" and a["dias"] == 69, a
    assert a["propietarios"] == ["Ana Prueba"], a
    b = por_unidad["1B"]
    assert (b["capital"], b["liquidaciones_vencidas"], b["vencida_desde"], b["dias"]) == (
        "40000.00", 1, "2026-11-10", 8), b
    assert b["propietarios"] == ["Carla Prueba"], f"el inquilino no es propietario: {b}"
    assert por_unidad["2A"]["propietarios"] == [], por_unidad["2A"]
    assert por_unidad["2A"]["total_vencido"] == "300.00", por_unidad["2A"]
    resumen = cuerpo["resumen"]
    total = sum(Decimal(f["total_vencido"]) for f in cuerpo["unidades"])
    assert resumen == {"unidades_con_deuda": 4, "morosos_criticos": 1, "total_vencido": f"{total:.2f}"}, resumen


def test_c02_una_deuda_pagada_en_partes_baja_y_despues_desaparece(mundo: Mundo) -> None:
    """Escenario: Deuda pagada en partes"""
    armar_la_base(mundo)
    antes = Decimal(filas(mundo)["1A"]["total_vencido"])
    pagar(mundo, "1A", "5000.00", date(2026, 11, 15))
    despues = filas(mundo)
    assert "1A" in despues, "pagó sólo una parte: tiene que seguir en la lista"
    assert Decimal(despues["1A"]["total_vencido"]) == antes - Decimal("5000.00"), despues["1A"]
    pagar(mundo, "1A", f"{antes - Decimal('5000.00'):.2f}", date(2026, 11, 16))
    final = filas(mundo)
    assert "1A" not in final, f"pagó todo: no tiene que aparecer: {final.get('1A')}"
    assert morosidad(mundo)["resumen"]["morosos_criticos"] == 0


def test_c03_los_morosos_criticos_primero_y_despues_de_mayor_a_menor(mundo: Mundo) -> None:
    armar_la_base(mundo)
    orden = [f["unidad"] for f in morosidad(mundo)["unidades"]]
    # `1B` ($40.000) debe más que `1A` (≈ $30.800), pero `1A` es moroso crítico.
    assert orden == ["1A", "1B", "2B", "2A"], orden


def test_c03_ante_un_empate_ordena_por_unidad(mundo: Mundo) -> None:
    emitir(mundo, NOV, ("2B", "1A"))
    pagar(mundo, "1A", "2000.00", date(2026, 11, 5))  # `1A` queda debiendo $8.000, igual que `2B`
    orden = [f["unidad"] for f in morosidad(mundo)["unidades"]]
    assert orden == ["1A", "2B"], orden


def test_c04_la_etiqueta_y_el_total_son_los_del_libro(mundo: Mundo) -> None:
    """Escenario: Una sola liquidación vencida"""
    armar_la_base(mundo)
    libro = situacion_del_libro(mundo)
    esperado = {u: v for u, v in libro.items() if v[0] != "sin_deuda_vencida"}
    obtenido = {f["unidad"]: (f["etiqueta"], f["total_vencido"]) for f in morosidad(mundo)["unidades"]}
    assert obtenido == esperado, f"API {obtenido} != libro {esperado}"
    assert obtenido["1A"][0] == "moroso_critico" and obtenido["1B"][0] == "con_deuda_vencida", obtenido
    assert obtenido["2A"][0] == "bajo_umbral", obtenido


def test_c05_si_de_la_mas_vieja_queda_solo_el_interes_la_antiguedad_sigue_desde_ella(mundo: Mundo) -> None:
    """Escenario: Sólo queda el interés de la más vieja"""
    emitir(mundo, SEP, ("1A",))
    pagar(mundo, "1A", MENSUAL["1A"], date(2026, 9, 25))  # el capital de septiembre, tarde
    emitir(mundo, OCT, ("1A",))  # registra el interés del 11 al 25/09
    assert intereses_registrados(mundo, "1A") > 0, "precondición: queda el interés de septiembre"
    fila = filas(mundo)["1A"]
    assert fila["vencida_desde"] == "2026-09-10", f"la más vieja con algo impago es septiembre: {fila}"
    assert fila["dias"] == (HOY - date(2026, 9, 10)).days, fila
    assert fila["liquidaciones_vencidas"] == 1, f"septiembre no tiene capital: sólo cuenta octubre: {fila}"
    assert fila["capital"] == MENSUAL["1A"], fila


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio", "contador",
                                 "contador_del_edificio", "auxiliar", "consejo"])
def test_c06_ven_la_morosidad_los_perfiles_con_alcance(mundo: Mundo, rol: str) -> None:
    armar_la_base(mundo)
    mundo.como("admin_principal")
    referencia = morosidad(mundo)
    mundo.como(rol)
    assert morosidad(mundo) == referencia, f"{rol} ve otra morosidad"


def test_c06_ver_morosidad_es_vocabulario_de_auditoria(mundo: Mundo) -> None:
    filas_ = mundo.filas("SELECT nombre FROM accion_de_auditoria WHERE nombre = 'ver_morosidad'")
    assert len(filas_) == 1, "la migración suma `ver_morosidad` al vocabulario de auditoría"


def test_n01_el_vecino_no_ve_la_morosidad(mundo: Mundo) -> None:
    """Escenario: El vecino no ve la morosidad"""
    armar_la_base(mundo)
    for vecino in ("ana", "carla", "beto"):
        mundo.como(vecino)
        sin_permiso(pedir(mundo))


@pytest.mark.parametrize("rol", ["admin_de_otro_edificio", "consejo_de_otro_edificio", "administracion_b"])
def test_n01_fuera_del_alcance_da_404(mundo: Mundo, rol: str) -> None:
    armar_la_base(mundo)
    mundo.como(rol)
    no_encontrado(pedir(mundo))


def test_n01_un_edificio_de_otra_administracion_da_404(mundo: Mundo) -> None:
    mundo.como("super_admin")
    no_encontrado(pedir(mundo, mundo.edificio_b))


def test_n02_una_sola_vencida_o_bajo_el_umbral_no_es_moroso_critico(mundo: Mundo) -> None:
    # `2B` debe septiembre y octubre pero sólo $300 en total: bajo el umbral, no moroso crítico.
    emitir(mundo, SEP, ("2B", "1B"))
    pagar(mundo, "2B", "7850.00", date(2026, 9, 5))
    emitir(mundo, OCT, ("2B", "1B"))
    pagar(mundo, "1B", "40000.00", date(2026, 10, 5))  # `1B` paga un mes de dos: una sola vencida con capital
    pagar(mundo, "2B", "7850.00", date(2026, 10, 5))
    por_unidad = filas(mundo)
    assert por_unidad["2B"]["liquidaciones_vencidas"] == 2, por_unidad["2B"]
    assert por_unidad["2B"]["etiqueta"] == "bajo_umbral", por_unidad["2B"]
    assert por_unidad["1B"]["etiqueta"] != "moroso_critico", por_unidad["1B"]
    assert morosidad(mundo)["resumen"]["morosos_criticos"] == 0


def test_n03_no_trae_datos_de_contacto(mundo: Mundo) -> None:
    armar_la_base(mundo)
    r = pedir(mundo)
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    texto = r.text.lower()
    assert EMAIL_DE_ANA not in texto, "la morosidad no muestra el email de nadie"
    for clave in ("email", "telefono", "dni", "documento"):
        assert f'"{clave}' not in texto, f"la morosidad no trae `{clave}`"


def test_n04_pedir_la_morosidad_no_escribe(mundo: Mundo) -> None:
    """Escenario: El libro queda igual"""
    armar_la_base(mundo)
    antes = del_libro(mundo)
    for rol in ("admin_principal", "consejo", "ana"):
        mundo.como(rol)
        pedir(mundo)
    mundo.como("admin_principal")
    morosidad(mundo)
    assert del_libro(mundo) == antes, "leer la morosidad escribió en el libro o en la auditoría"


def test_n05_al_dia_con_credito_a_favor_o_con_la_emision_anulada_no_aparece(mundo: Mundo) -> None:
    emitir(mundo, SEP, ("1A", "1B", "2B"))
    pagar(mundo, "1B", MENSUAL["1B"], date(2026, 9, 5))
    pagar(mundo, "2B", "9000.00", date(2026, 9, 5))  # $1.000 a favor
    octubre = emitir(mundo, OCT, ("1A", "1B"))
    anular(mundo, octubre)  # `1B` sólo debía octubre
    por_unidad = filas(mundo)
    assert "2B" not in por_unidad, f"al día y con crédito a favor: {por_unidad.get('2B')}"
    assert "1B" not in por_unidad, f"su única deuda es de una emisión anulada: {por_unidad.get('1B')}"
    assert por_unidad["1A"]["capital"] == MENSUAL["1A"], f"la anulada no cuenta para `1A`: {por_unidad['1A']}"


def test_n06_el_interes_corrido_despues_del_ultimo_corte_no_se_suma(mundo: Mundo) -> None:
    armar_la_base(mundo)
    b = filas(mundo)["1B"]
    # Noviembre venció el 10/11: hasta hoy corrieron 8 días de interés que todavía no se registraron.
    assert b["intereses"] == "0.00" and b["total_vencido"] == "40000.00", b


def test_n06_sin_intereses_registrados_la_fecha_de_los_intereses_es_nula(mundo: Mundo) -> None:
    emitir(mundo, NOV, ("1A",))
    cuerpo = morosidad(mundo)
    assert cuerpo["intereses_al"] is None, cuerpo["intereses_al"]
    assert [f["unidad"] for f in cuerpo["unidades"]] == ["1A"], cuerpo["unidades"]
