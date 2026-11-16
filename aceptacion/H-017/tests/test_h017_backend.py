"""H-017 · lo de backend: el `obligacion_id` de cada unidad (C03) y el nombre del PDF (C04, N03)."""

from __future__ import annotations

import re

from ._h017 import (
    NOV,
    Mundo,
    cargar_base,
    documento,
    documentos,
    emitir_lo_revisado,
    enlace,
    generar_todos,
    leer_liquidacion,
    obligacion_del_periodo,
    unidad,
)


def test_c03_cada_unidad_trae_su_obligacion(mundo: Mundo) -> None:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    leida = leer_liquidacion(mundo, liquidacion)
    for u in ("1A", "1B", "2A", "2B"):
        assert unidad(leida, u).get("obligacion_id") == str(obligacion_del_periodo(mundo, u, NOV)), u


def test_c03_sin_obligacion_es_null(mundo: Mundo) -> None:
    from ._h017 import configurar, gasto

    configurar(mundo)
    gasto(mundo, "40000.00", categoria="Ascensor", grupo=mundo.ascensor)
    leida = leer_liquidacion(mundo, emitir_lo_revisado(mundo)["liquidacion_id"])
    assert "obligacion_id" in unidad(leida, "1A") and unidad(leida, "1A")["obligacion_id"] is None


def _nombre(mundo: Mundo, identificador: str, variante: str) -> str:
    cargar_base(mundo)
    liquidacion = emitir_lo_revisado(mundo)["liquidacion_id"]
    generar_todos(mundo, liquidacion)
    doc = documento(documentos(mundo, liquidacion), identificador, variante)["documento_id"]
    r = enlace(mundo, doc, variante)
    assert r.status_code == 201, r.text[:200]
    d = mundo.cliente.get(r.json()["url"])
    assert d.status_code == 200
    cabecera = d.headers.get("content-disposition", "")
    m = re.fullmatch(r'attachment; filename="([^"]+)"', cabecera)
    assert m, f"Content-Disposition inesperado: {cabecera!r}"
    return m.group(1)


def test_c04_el_pdf_baja_con_periodo_unidad_y_variante(mundo: Mundo) -> None:
    assert _nombre(mundo, "1B", "completa") == "expensa-2026-11-1b-completa.pdf"


def test_c04_la_variante_del_inquilino(mundo: Mundo) -> None:
    assert _nombre(mundo, "1B", "sin_extraordinaria") == "expensa-2026-11-1b-sin-extraordinaria.pdf"


def test_n03_el_nombre_no_lleva_datos_personales(mundo: Mundo) -> None:
    nombre = _nombre(mundo, "2A", "completa")
    assert re.fullmatch(r"[a-z0-9.-]+", nombre), nombre
    assert "ficticia" not in nombre and "persona" not in nombre
