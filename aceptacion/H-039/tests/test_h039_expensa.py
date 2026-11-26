"""H-039 · la expensa explicada (C01 a C03). Contrato en `aceptacion/H-039/CONTRATO.md`."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ._h039 import (
    CLAVES_DE_CATEGORIA,
    CLAVES_DE_CATEGORIA_COMPARADA,
    CLAVES_DE_GRUPO,
    CLAVES_DE_GRUPO_DEL_INQUILINO,
    CLAVES_DE_LA_COMPARACION,
    Mundo,
    anular_liquidacion,
    base_dos_meses,
    base_solo_octubre,
    del_administrador,
    detalle_ok,
    emitir_lo_revisado,
    linea_del_administrador,
    lista_ok,
    sembrar_noviembre,
)
from ._h039 import OCT as OCTUBRE


def _suma(*valores: str) -> str:
    return f"{sum((Decimal(v) for v in valores), Decimal('0.00')):.2f}"


def _grupos_esperados(m: Mundo, liquidacion: str, identificador: str, *, extraordinaria: bool) -> list[dict[str, Any]]:
    """Los grupos de la liquidación en los que participa la unidad, tal como los ve el administrador del 7."""
    admin = del_administrador(m, liquidacion)
    linea = linea_del_administrador(m, liquidacion, identificador)
    propios = {g["grupo_id"]: g for g in linea["por_grupo"]}
    resultado = []
    for g in admin["grupos"]:
        if g["grupo_id"] in propios:
            fila = {"grupo_id": g["grupo_id"], "nombre": g["nombre"], "ordinaria": propios[g["grupo_id"]]["ordinaria"]}
            if extraordinaria:
                fila["extraordinaria"] = propios[g["grupo_id"]]["extraordinaria"]
            resultado.append(fila)
    return resultado


# --- C01: la lista y el detalle -------------------------------------------------------------------------


def test_c01_la_lista_trae_las_emitidas_de_la_unidad_la_mas_nueva_primero(mundo: Mundo) -> None:
    """Escenario: Ana abre las expensas de su `1A`"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    lista = lista_ok(mundo, "1A")
    assert [(f["liquidacion_id"], f["periodo"], f["vencimiento"], f["total"]) for f in lista] == [
        (meses.liq_nov, "2026-11-01", "2026-11-10", "46500.00"),
        (meses.liq_oct, "2026-10-01", "2026-10-10", "31200.00"),
    ], lista


def test_c01_la_lista_no_trae_lo_no_emitido_ni_lo_anulado(mundo: Mundo) -> None:
    """Escenario: noviembre con gastos aprobados pero sin emitir, y después emitido y anulado"""
    meses = base_solo_octubre(mundo)
    sembrar_noviembre(mundo)
    mundo.como("ana")
    assert [f["liquidacion_id"] for f in lista_ok(mundo, "1A")] == [meses.liq_oct], "noviembre sin emitir no figura"
    mundo.como("super_admin")
    nov = str(emitir_lo_revisado(mundo)["liquidacion_id"])
    mundo.como("ana")
    assert [f["liquidacion_id"] for f in lista_ok(mundo, "1A")] == [nov, meses.liq_oct], "emitida, figura"
    mundo.como("super_admin")
    anular_liquidacion(mundo, nov)
    mundo.como("ana")
    assert [f["liquidacion_id"] for f in lista_ok(mundo, "1A")] == [meses.liq_oct], "anulada, no figura"


def test_c01_el_detalle_de_1a_cierra_al_centavo_con_lo_emitido(mundo: Mundo) -> None:
    """Escenario: Ana lee noviembre de su `1A`: categorías con subtotal, su parte por grupo, fondo y total"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    d = detalle_ok(mundo, "1A", meses.liq_nov)
    assert (d["liquidacion_id"], d["unidad_id"], d["identificador"], d["vinculo"], d["periodo"], d["vencimiento"]) == (
        meses.liq_nov, str(mundo.unidades["1A"]), "1A", "propietario", "2026-11-01", "2026-11-10"), d
    assert d["complejo_id"] == str(mundo.edificio), d
    # los números de la unidad, a mano
    assert (d["ordinaria"], d["fondo_de_reserva"], d["extraordinaria"], d["intereses"], d["total"]) == (
        "30000.00", "1500.00", "15000.00", "0.00", "46500.00"), d
    assert d["cargos_particulares"] == [], d["cargos_particulares"]
    # las categorías con su subtotal, como las ve el administrador (R16): nunca recalculadas
    admin = del_administrador(mundo, meses.liq_nov)
    assert d["bloques"] == admin["bloques"], d["bloques"]
    assert d["bloques"]["ordinario"]["subtotal"] == "140000.00", d["bloques"]
    assert d["bloques"]["extraordinario"]["subtotal"] == "50000.00", d["bloques"]
    assert [(c["nombre"], c["importe"]) for c in d["bloques"]["ordinario"]["categorias"]] == [
        ("Limpieza", "100000.00"), ("Ascensor", "40000.00")], d["bloques"]
    assert all(set(c) == CLAVES_DE_CATEGORIA for b in d["bloques"].values() for c in b["categorias"]), d["bloques"]
    # su parte por grupo de reparto: sólo los grupos donde participa
    assert d["grupos"] == _grupos_esperados(mundo, meses.liq_nov, "1A", extraordinaria=True), d["grupos"]
    assert [(g["nombre"], g["ordinaria"], g["extraordinaria"]) for g in d["grupos"]] == [
        ("Generales", "30000.00", "15000.00")], d["grupos"]
    assert all(set(g) == CLAVES_DE_GRUPO for g in d["grupos"]), d["grupos"]
    # cierra con lo emitido para la unidad: la obligación del libro y la línea del administrador
    obligacion = next(o for o in meses.noviembre["obligaciones"] if o["identificador"] == "1A")
    assert _suma(d["ordinaria"], *(c["importe"] for c in d["cargos_particulares"])) == obligacion["ordinaria"], d
    assert d["fondo_de_reserva"] == obligacion["fondo_de_reserva"], d
    assert d["extraordinaria"] == obligacion["extraordinaria"], d
    linea = linea_del_administrador(mundo, meses.liq_nov, "1A")
    assert d["total"] == linea["total"] == _suma(
        d["ordinaria"], d["fondo_de_reserva"], d["extraordinaria"], d["intereses"], *(c["importe"] for c in d["cargos_particulares"])), d


def test_c01_el_detalle_de_2b_reparte_por_los_dos_grupos(mundo: Mundo) -> None:
    """Escenario: Ana lee noviembre de su `2B`, que participa de Generales y de Ascensor"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    d = detalle_ok(mundo, "2B", meses.liq_nov)
    assert (d["ordinaria"], d["fondo_de_reserva"], d["extraordinaria"], d["intereses"], d["total"]) == (
        "30000.00", "1500.00", "7500.00", "0.00", "39000.00"), d
    assert [(g["nombre"], g["ordinaria"], g["extraordinaria"]) for g in d["grupos"]] == [
        ("Generales", "15000.00", "7500.00"), ("Ascensor", "15000.00", "0.00")], d["grupos"]
    assert d["grupos"] == _grupos_esperados(mundo, meses.liq_nov, "2B", extraordinaria=True), d["grupos"]
    obligacion = next(o for o in meses.noviembre["obligaciones"] if o["identificador"] == "2B")
    assert (d["ordinaria"], d["fondo_de_reserva"], d["extraordinaria"]) == (
        obligacion["ordinaria"], obligacion["fondo_de_reserva"], obligacion["extraordinaria"]), d
    assert d["total"] == linea_del_administrador(mundo, meses.liq_nov, "2B")["total"], d


def test_c01_los_cargos_particulares_de_la_unidad_figuran_y_el_total_cierra(mundo: Mundo) -> None:
    """Escenario: Carla lee noviembre de su `1B`, con una multa de 5.000,00"""
    meses = base_dos_meses(mundo)
    mundo.como("carla")
    d = detalle_ok(mundo, "1B", meses.liq_nov)
    assert d["cargos_particulares"] == [{"concepto": "Multa", "importe": "5000.00"}], d["cargos_particulares"]
    assert (d["ordinaria"], d["total"]) == ("30000.00", "51500.00"), d
    obligacion = next(o for o in meses.noviembre["obligaciones"] if o["identificador"] == "1B")
    assert _suma(d["ordinaria"], "5000.00") == obligacion["ordinaria"] == "35000.00", d
    assert d["total"] == linea_del_administrador(mundo, meses.liq_nov, "1B")["total"], d


def test_c01_el_detalle_de_octubre_sale_de_lo_emitido_en_octubre(mundo: Mundo) -> None:
    """Escenario: Ana lee octubre de su `1A`, con noviembre ya emitido"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    d = detalle_ok(mundo, "1A", meses.liq_oct)
    assert (d["periodo"], d["ordinaria"], d["fondo_de_reserva"], d["extraordinaria"], d["total"]) == (
        "2026-10-01", "24000.00", "1200.00", "6000.00", "31200.00"), d
    assert d["bloques"]["extraordinario"]["subtotal"] == "20000.00", d["bloques"]


# --- C02: propietario e inquilino ------------------------------------------------------------------------


def test_c02_el_propietario_ve_ordinarias_y_extraordinarias(mundo: Mundo) -> None:
    """Escenario: Carla, propietaria de `1B`, lee noviembre"""
    meses = base_dos_meses(mundo)
    mundo.como("carla")
    d = detalle_ok(mundo, "1B", meses.liq_nov)
    assert d["vinculo"] == "propietario", d
    assert set(d["bloques"]) == {"ordinario", "extraordinario"}, sorted(d["bloques"])
    assert d["extraordinaria"] == "15000.00", d
    assert [(c["nombre"], c["importe"]) for c in d["bloques"]["extraordinario"]["categorias"]] == [
        ("Pintura", "50000.00")], d["bloques"]
    assert [f["total"] for f in lista_ok(mundo, "1B")] == ["51500.00", "31200.00"], "su lista, completa"


def test_c02_el_inquilino_ve_lo_de_la_variante_sin_extraordinaria(mundo: Mundo) -> None:
    """Escenario: Beto, inquilino de `1B`, lee noviembre: interés, ordinaria y fondo, sin la extraordinaria"""
    meses = base_dos_meses(mundo)
    mundo.como("beto")
    d = detalle_ok(mundo, "1B", meses.liq_nov, inquilino=True)
    assert d["vinculo"] == "inquilino", d
    assert set(d["bloques"]) == {"ordinario"}, sorted(d["bloques"])
    assert d["bloques"]["ordinario"] == del_administrador(mundo, meses.liq_nov)["bloques"]["ordinario"], d["bloques"]
    assert all(set(g) == CLAVES_DE_GRUPO_DEL_INQUILINO for g in d["grupos"]), d["grupos"]
    assert d["grupos"] == _grupos_esperados(mundo, meses.liq_nov, "1B", extraordinaria=False), d["grupos"]
    assert d["cargos_particulares"] == [{"concepto": "Multa", "importe": "5000.00"}], d["cargos_particulares"]
    assert (d["ordinaria"], d["fondo_de_reserva"], d["intereses"], d["total"]) == (
        "30000.00", "1500.00", "0.00", "36500.00"), d
    # es lo mismo que la deuda sin extraordinaria que ya ve en `mis-unidades` (H-038) y que el libro emitió
    obligacion = next(o for o in meses.noviembre["obligaciones"] if o["identificador"] == "1B")
    assert d["total"] == _suma(obligacion["ordinaria"], obligacion["fondo_de_reserva"], d["intereses"]), d
    assert [(f["periodo"], f["total"]) for f in lista_ok(mundo, "1B")] == [
        ("2026-11-01", "36500.00"), ("2026-10-01", "25200.00")], "su lista, sin la extraordinaria"


# --- C03: la comparación con la emisión anterior ---------------------------------------------------------


def test_c03_la_comparacion_da_la_diferencia_del_total_y_por_categoria(mundo: Mundo) -> None:
    """Escenario: Ana compara noviembre con octubre en su `1A`"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    c = detalle_ok(mundo, "1A", meses.liq_nov)["comparacion"]
    assert isinstance(c, dict), f"la comparación tiene que ser un objeto: {c!r}"
    assert set(c) == CLAVES_DE_LA_COMPARACION, sorted(c)
    assert (c["liquidacion_id"], c["periodo"]) == (meses.liq_oct, "2026-10-01"), c
    assert (c["total_anterior"], c["diferencia_total"]) == ("31200.00", "15300.00"), c
    assert c["total_anterior"] == linea_del_administrador(mundo, meses.liq_oct, "1A")["total"], c
    assert all(set(x) == CLAVES_DE_CATEGORIA_COMPARADA for x in c["categorias"]), c["categorias"]
    por_nombre = {x["nombre"]: x for x in c["categorias"]}
    assert {n: (x["bloque"], x["importe"], x["importe_anterior"], x["diferencia"]) for n, x in por_nombre.items()} == {
        "Limpieza": ("ordinario", "100000.00", "80000.00", "20000.00"),
        "Ascensor": ("ordinario", "40000.00", "0.00", "40000.00"),
        "Pintura": ("extraordinario", "50000.00", "20000.00", "30000.00"),
    }, c["categorias"]


def test_c03_la_comparacion_del_inquilino_es_la_suya(mundo: Mundo) -> None:
    """Escenario: Beto compara noviembre con octubre: sin la extraordinaria"""
    meses = base_dos_meses(mundo)
    mundo.como("beto")
    c = detalle_ok(mundo, "1B", meses.liq_nov, inquilino=True)["comparacion"]
    assert isinstance(c, dict), f"la comparación tiene que ser un objeto: {c!r}"
    assert (c["periodo"], c["total_anterior"], c["diferencia_total"]) == ("2026-10-01", "25200.00", "11300.00"), c
    assert sorted((x["nombre"], x["bloque"]) for x in c["categorias"]) == [
        ("Ascensor", "ordinario"), ("Limpieza", "ordinario")], c["categorias"]


def test_c03_sin_anterior_no_hay_comparacion(mundo: Mundo) -> None:
    """Escenario: octubre es la primera liquidación del edificio"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    d = detalle_ok(mundo, "1A", meses.liq_oct)
    assert d["comparacion"] is None, f"sin anterior la comparación es null: {d['comparacion']!r}"


def test_c03_la_anterior_es_la_emitida_vigente_no_la_anulada(mundo: Mundo) -> None:
    """Escenario: octubre se anula y se vuelve a emitir antes de emitir noviembre"""
    meses = base_solo_octubre(mundo)
    anular_liquidacion(mundo, meses.liq_oct)
    nueva = str(emitir_lo_revisado(mundo, OCTUBRE)["liquidacion_id"])
    assert nueva != meses.liq_oct
    sembrar_noviembre(mundo)
    nov = str(emitir_lo_revisado(mundo)["liquidacion_id"])
    mundo.como("ana")
    c = detalle_ok(mundo, "1A", nov)["comparacion"]
    assert isinstance(c, dict), f"la comparación tiene que ser un objeto: {c!r}"
    assert (c["liquidacion_id"], c["periodo"]) == (nueva, "2026-10-01"), c
