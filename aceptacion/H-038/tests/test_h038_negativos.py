"""H-038 · lo que no tiene que pasar (N01 a N04). Contrato en `aceptacion/H-038/CONTRATO.md`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from ._h038 import (
    Mundo,
    base_con_mora,
    base_noviembre,
    cargo,
    cargo_de,
    conteo_de_todo,
    del_libro,
    documentos_de,
    generar_los_pdfs,
    informar_ok,
    mis_unidades,
    morosidad_del_administrador,
    no_encontrado,
    pago_confirmado,
    pagos_de,
    por_unidad,
    rechazar_como_administrador,
    revertir_como_administrador,
    ruta_unidad,
    texto_del_pdf,
)


def _rutas(m: Mundo, unidad: str | UUID, cargo_id: UUID) -> dict[str, str]:
    return {
        "pagos": ruta_unidad(m, unidad, "/pagos"),
        "documentos": ruta_unidad(m, unidad, "/documentos"),
        "cargo": ruta_unidad(m, unidad, f"/cargos-particulares/{cargo_id}"),
    }


# --- N01: la unidad ajena no existe ---------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["pagos", "documentos", "cargo"])
def test_n01_una_unidad_ajena_del_mismo_edificio_da_404(mundo: Mundo, ruta: str) -> None:
    """Escenario: Ana pide la `2A` de Dora"""
    liquidacion = base_noviembre(mundo)
    generar_los_pdfs(mundo, liquidacion)
    propio = cargo(mundo, "1A", "2500.00", concepto="Multa de 1A")
    ajeno = cargo(mundo, "2A", "700.00", concepto="Multa de 2A")
    mundo.como("ana")
    assert mundo.cliente.get(_rutas(mundo, "1A", propio)[ruta]).status_code == 200, "control: su unidad responde"
    no_encontrado(mundo.cliente.get(_rutas(mundo, "2A", ajeno)[ruta]), f"{ruta} de 2A")


@pytest.mark.parametrize("ruta", ["pagos", "documentos", "cargo"])
def test_n01_una_unidad_de_otro_edificio_da_404(mundo: Mundo, ruta: str) -> None:
    """Escenario: Beto pide la `9A` del otro edificio de la misma administración"""
    base_noviembre(mundo)
    ajeno = cargo(mundo, "9A", "900.00", concepto="Multa de 9A", complejo=mundo.otro, unidad_id=mundo.unidad_otro)
    propio = cargo(mundo, "1B", "400.00", concepto="Cargo de 1B")
    mundo.como("beto")
    assert mundo.cliente.get(_rutas(mundo, "1B", propio)[ruta]).status_code == 200, "control: su unidad responde"
    no_encontrado(mundo.cliente.get(_rutas(mundo, "9A", ajeno)[ruta]), f"{ruta} de 9A")


@pytest.mark.parametrize("ruta", ["pagos", "documentos", "cargo"])
def test_n01_una_unidad_de_otra_administracion_da_404(mundo: Mundo, ruta: str) -> None:
    """Escenario: Una persona de la administración B pide la `1A` de la A"""
    base_noviembre(mundo)
    propio = cargo(mundo, "1A", "2500.00", concepto="Multa de 1A")
    mundo.como("ana")
    assert mundo.cliente.get(_rutas(mundo, "1A", propio)[ruta]).status_code == 200, "control: su unidad responde"
    mundo.como("administracion_b")
    no_encontrado(mundo.cliente.get(_rutas(mundo, "1A", propio)[ruta]), f"{ruta} de otra administración")
    no_encontrado(mundo.cliente.get(_rutas(mundo, mundo.unidad_b, propio)[ruta]),
                  f"{ruta} de una unidad de la administración B sin vínculo")


@pytest.mark.parametrize("quien", ["super_admin", "admin_principal", "contador", "consejo"])
def test_n01_el_personal_no_entra_por_el_portal_a_una_unidad_sin_vinculo(mundo: Mundo, quien: str) -> None:
    """Escenario: El portal es del vecino, no del equipo"""
    base_noviembre(mundo)
    multa = cargo(mundo, "1A", "2500.00", concepto="Multa de 1A")
    mundo.como("ana")
    assert mundo.cliente.get(ruta_unidad(mundo, "1A", "/pagos")).status_code == 200, "control"
    mundo.como(quien)
    for sufijo in ("/pagos", "/documentos", f"/cargos-particulares/{multa}"):
        no_encontrado(mundo.cliente.get(ruta_unidad(mundo, "1A", sufijo)), f"{quien} en {sufijo}")


def test_n01_un_cargo_de_otra_unidad_o_sin_aprobar_da_404(mundo: Mundo) -> None:
    """Escenario: El id del cargo existe pero no es de la unidad que se pide, o no está aprobado"""
    base_noviembre(mundo)
    de_1a = cargo(mundo, "1A", "2500.00", concepto="Multa de 1A")
    de_2b = cargo(mundo, "2B", "300.00", concepto="Multa de 2B")
    borrador = cargo(mundo, "1A", "100.00", concepto="Borrador de 1A", estado="borrador")
    mundo.como("ana")
    assert cargo_de(mundo, "1A", de_1a).status_code == 200, "control: su cargo aprobado"
    assert cargo_de(mundo, "2B", de_2b).status_code == 200, "control: el de su otra unidad"
    no_encontrado(cargo_de(mundo, "2B", de_1a), "el cargo de 1A por la ruta de 2B")
    no_encontrado(cargo_de(mundo, "1A", borrador), "un cargo en borrador de su propia unidad")
    no_encontrado(cargo_de(mundo, "1A", uuid4()), "un cargo que no existe")
    no_encontrado(mundo.cliente.get(ruta_unidad(mundo, uuid4(), "/pagos")), "una unidad que no existe")


# --- N02: el inquilino no ve lo extraordinario -----------------------------------------------------------


def test_n02_el_inquilino_no_recibe_montos_extraordinarios_en_los_totales(mundo: Mundo) -> None:
    """Escenario: Beto debe 33.350,00 y Carla 48.350,00 de la misma `1B`"""
    base_noviembre(mundo)
    assert del_libro(mundo, "1B")["total_a_pagar"] == "48350.00", "control: el libro de 1B"
    mundo.como("beto")
    antes = mis_unidades(mundo)
    assert por_unidad(mundo)["1B"]["total_a_pagar"] == "33350.00", antes
    assert antes["conjunto"]["total_a_pagar"] == "33350.00", antes["conjunto"]
    assert "extraordinaria" not in str(antes), f"ni una clave ni un valor extraordinario: {antes}"
    pago_confirmado(mundo, "beto", {"1B": "33350.00"}, numero="OP-0010")
    assert del_libro(mundo, "1B")["total_a_pagar"] == "15000.00", "control: al libro le queda la extraordinaria"
    assert por_unidad(mundo)["1B"]["total_a_pagar"] == "0.00", "el inquilino ya no debe nada"
    assert por_unidad(mundo)["1B"]["vencimiento"] is None, "y no tiene vencimiento"
    mundo.como("carla")
    assert por_unidad(mundo)["1B"]["total_a_pagar"] == "15000.00", "la propietaria sigue debiendo la extraordinaria"


def test_n02_el_inquilino_no_ve_en_los_pagos_lo_que_fue_a_la_extraordinaria(mundo: Mundo) -> None:
    """Escenario: Beto paga 40.000,00 (33.350,00 más 6.650,00) y Carla paga el resto de la extraordinaria"""
    base_noviembre(mundo)
    de_beto = pago_confirmado(mundo, "beto", {"1B": "40000.00"}, numero="OP-0011", fecha="2026-11-04")
    de_carla = pago_confirmado(mundo, "carla", {"1B": "8350.00"}, numero="OP-0012", fecha="2026-11-06")
    assert del_libro(mundo, "1B")["total_a_pagar"] == "0.00", "control: 1B quedó al día"
    mundo.como("carla")
    propietaria = pagos_de(mundo, "1B")
    assert [(p["pago_id"], p["importe"]) for p in propietaria] == [(de_carla, "8350.00"), (de_beto, "40000.00")], (
        propietaria)
    mundo.como("beto")
    inquilino = pagos_de(mundo, "1B")
    assert [(p["pago_id"], p["importe"]) for p in inquilino] == [(de_beto, "33350.00")], (
        f"el inquilino ve de su pago sólo lo imputado a interés, ordinaria y fondo, y no el pago que fue entero "
        f"a la extraordinaria: {inquilino}")


def test_n02_el_inquilino_no_recibe_el_pdf_completo(mundo: Mundo) -> None:
    """Escenario: La expensa de `1B` según el vínculo"""
    liquidacion = base_noviembre(mundo)
    generar_los_pdfs(mundo, liquidacion)
    mundo.como("carla")
    propietaria = documentos_de(mundo, "1B")
    assert [d["variante"] for d in propietaria] == ["completa"], propietaria
    assert "48.350,00" in texto_del_pdf(mundo.cliente.get(propietaria[0]["url"]).content), "control"
    mundo.como("beto")
    inquilino = documentos_de(mundo, "1B")
    assert [d["variante"] for d in inquilino] == ["sin_extraordinaria"], inquilino
    bajado = mundo.cliente.get(inquilino[0]["url"])
    assert bajado.status_code == 200 and bajado.content.startswith(b"%PDF"), bajado.status_code
    texto = texto_del_pdf(bajado.content)
    assert "33.350,00" in texto, texto[:400]
    for ausente in ("Pintura", "15.000,00", "48.350,00"):
        assert ausente not in texto, f"el PDF del inquilino muestra «{ausente}»"


# --- N03: sólo lo confirmado -----------------------------------------------------------------------------


def test_n03_los_pagos_sin_confirmar_rechazados_o_revertidos_no_aparecen(mundo: Mundo) -> None:
    """Escenario: Ana informó cuatro pagos y sólo uno sigue confirmado"""
    base_noviembre(mundo)
    mundo.como("ana")
    informado = informar_ok(mundo, {"1A": "1000.00"}, numero="OP-0020")
    rechazado = informar_ok(mundo, {"1A": "2000.00"}, numero="OP-0021")
    rechazar_como_administrador(mundo, rechazado, volver_a="ana")
    revertido = pago_confirmado(mundo, "ana", {"1A": "3000.00"}, numero="OP-0022")
    revertir_como_administrador(mundo, revertido, volver_a="ana")
    vigente = pago_confirmado(mundo, "ana", {"1A": "4000.00"}, numero="OP-0023")
    lista = pagos_de(mundo, "1A")
    assert [p["pago_id"] for p in lista] == [vigente], (
        f"sólo el confirmado vigente; el informado {informado}, el rechazado {rechazado} y el revertido "
        f"{revertido} no: {lista}")


# --- N04: leer no escribe y los números son los del administrador ---------------------------------------


def test_n04_ninguna_lectura_escribe_en_la_base(mundo: Mundo) -> None:
    """Escenario: Ana recorre todo el portal"""
    liquidacion = base_noviembre(mundo)
    generar_los_pdfs(mundo, liquidacion)
    multa = cargo(mundo, "1A", "2500.00", concepto="Multa de 1A")
    pago_confirmado(mundo, "ana", {"1A": "1000.00"}, numero="OP-0030")
    antes = conteo_de_todo(mundo)
    mis_unidades(mundo)
    for unidad in ("1A", "2B", "9A"):
        pagos_de(mundo, unidad)
        for d in documentos_de(mundo, unidad):
            assert mundo.cliente.get(d["url"]).status_code == 200
    assert cargo_de(mundo, "1A", multa).status_code == 200
    despues = conteo_de_todo(mundo)
    assert despues == antes, f"tablas que cambiaron: {sorted(t for t in antes if antes[t] != despues.get(t))}"


def test_n04_los_numeros_del_portal_son_los_del_administrador_despues_de_pagar(mundo: Mundo) -> None:
    """Escenario: Carla paga parte de `1B` y el administrador y ella miran la misma deuda"""
    base_con_mora(mundo)
    pago_confirmado(mundo, "carla", {"1B": "20000.00"}, numero="OP-0040", fecha="2026-11-05")
    fila = por_unidad(mundo)["1B"]
    libro = del_libro(mundo, "1B")
    assert fila["total_a_pagar"] == libro["total_a_pagar"] == "28350.00", (fila, libro)
    visto = morosidad_del_administrador(mundo)["1B"]
    assert Decimal(visto["total_vencido"]) == Decimal(fila["total_a_pagar"]), (fila, visto)
    assert date.fromisoformat(fila["vencimiento"]) < date(2026, 11, 18), fila
