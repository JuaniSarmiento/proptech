"""H-038 · lo que pagué y mis PDFs (C04 a C06). Contrato en `aceptacion/H-038/CONTRATO.md`."""

from __future__ import annotations

from ._h038 import (
    CLAVES_DE_CARGO,
    Mundo,
    anular_liquidacion,
    base_noviembre,
    cargo,
    cargo_de,
    documentos_de,
    generar_los_pdfs,
    pago_confirmado,
    pagos_de,
    texto_del_pdf,
)

# --- C04: los pagos confirmados -------------------------------------------------------------------------


def test_c04_los_pagos_confirmados_de_cada_unidad_con_fecha_e_importe(mundo: Mundo) -> None:
    """Escenario: Un pago de dos unidades se parte por unidad"""
    base_noviembre(mundo)
    pago = pago_confirmado(mundo, "ana", {"1A": "10000.00", "2B": "5000.00"}, numero="OP-0001", fecha="2026-11-05")
    uno = pagos_de(mundo, "1A")
    assert uno == [{"pago_id": pago, "fecha_de_transferencia": "2026-11-05", "importe": "10000.00",
                    "banco": "Banco Nación", "numero_de_operacion": "OP-0001"}], uno
    dos = pagos_de(mundo, "2B")
    assert [(p["pago_id"], p["importe"]) for p in dos] == [(pago, "5000.00")], dos
    assert pagos_de(mundo, "9A") == [], "una unidad sin pagos devuelve la lista vacía"


def test_c04_los_pagos_vienen_del_mas_nuevo_al_mas_viejo(mundo: Mundo) -> None:
    """Escenario: Dos pagos de la misma unidad"""
    base_noviembre(mundo)
    viejo = pago_confirmado(mundo, "ana", {"1A": "1000.00"}, numero="OP-0002", fecha="2026-11-03")
    nuevo = pago_confirmado(mundo, "ana", {"1A": "2000.00"}, numero="OP-0003", fecha="2026-11-07")
    lista = pagos_de(mundo, "1A")
    assert [(p["pago_id"], p["fecha_de_transferencia"]) for p in lista] == [
        (nuevo, "2026-11-07"), (viejo, "2026-11-03")], lista


# --- C05: los PDFs ---------------------------------------------------------------------------------------


def test_c05_el_pdf_es_de_un_periodo_emitido_con_el_enlace_firmado_del_7(mundo: Mundo) -> None:
    """Escenario: Ana descarga la expensa de noviembre de su `1A`"""
    liquidacion = base_noviembre(mundo)
    generar_los_pdfs(mundo, liquidacion)
    mundo.como("ana")
    lista = documentos_de(mundo, "1A")
    assert len(lista) == 1, f"un período emitido, una variante: {lista}"
    d = lista[0]
    assert (d["periodo"], d["variante"], d["liquidacion_id"], d["complejo_id"]) == (
        "2026-11-01", "completa", liquidacion, str(mundo.edificio)), d
    assert d["url"].startswith("/api/documentos/descarga?token="), d["url"]
    bajado = mundo.cliente.get(d["url"])
    assert bajado.status_code == 200 and bajado.content.startswith(b"%PDF"), bajado.status_code
    texto = texto_del_pdf(bajado.content)
    assert "TF-1A" in texto and "43.350,00" in texto and "Pintura" in texto, texto[:400]
    assert {x["periodo"] for x in documentos_de(mundo, "2B")} == {"2026-11-01"}, "el octubre sin emitir no aparece"
    assert documentos_de(mundo, "9A") == [], "el otro edificio no emitió nada"


def test_c05_un_pdf_que_todavia_no_se_genero_no_aparece(mundo: Mundo) -> None:
    """Escenario: La expensa está emitida pero el PDF sigue pendiente"""
    base_noviembre(mundo)
    mundo.como("ana")
    assert documentos_de(mundo, "1A") == [], "un documento `pendiente` no se ofrece"


def test_c05_una_liquidacion_anulada_no_se_ofrece(mundo: Mundo) -> None:
    """Escenario: El administrador anuló la liquidación"""
    liquidacion = base_noviembre(mundo)
    generar_los_pdfs(mundo, liquidacion)
    mundo.como("ana")
    assert len(documentos_de(mundo, "1A")) == 1, "control: antes de anular se ofrece"
    mundo.como("super_admin")
    anular_liquidacion(mundo, liquidacion)
    mundo.como("ana")
    assert documentos_de(mundo, "1A") == [], "una liquidación anulada no se descarga"


# --- C06: el cargo particular ----------------------------------------------------------------------------


def test_c06_el_vecino_lee_su_cargo_particular_por_id(mundo: Mundo) -> None:
    """Escenario: Ana ve la multa de su `1A` (cierra D3 del 6)"""
    base_noviembre(mundo)
    multa = cargo(mundo, "1A", "2500.00", concepto="Multa de 1A")
    mundo.como("admin_principal")
    del_administrador = mundo.cliente.get(f"/api/cargos-particulares/{multa}")
    assert del_administrador.status_code == 200, del_administrador.text[:200]
    mundo.como("ana")
    r = cargo_de(mundo, "1A", multa)
    assert r.status_code == 200, f"se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    assert set(r.json()) == CLAVES_DE_CARGO, sorted(r.json())
    assert r.json() == del_administrador.json(), "el vecino ve lo mismo que el administrador"
    assert (r.json()["concepto"], r.json()["importe"], r.json()["unidad_id"]) == (
        "Multa de 1A", "2500.00", str(mundo.unidades["1A"]))


def test_c06_el_inquilino_tambien_lee_el_cargo_de_su_unidad(mundo: Mundo) -> None:
    """Escenario: El cargo de 5.000,00 de `1B` está dentro de la ordinaria del inquilino"""
    base_noviembre(mundo)
    id_del_cargo = mundo.uno("SELECT id FROM cargo_particular WHERE concepto = 'Multa' AND unidad_id = %s",
                             (mundo.unidades["1B"],))
    for quien in ("beto", "carla"):
        mundo.como(quien)
        r = cargo_de(mundo, "1B", id_del_cargo)
        assert r.status_code == 200, f"{quien}: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
        assert r.json()["importe"] == "5000.00", r.json()
