"""H-026 · C04: la unidad vigente de cada parte en la lista de pagos. Contrato en `aceptacion/H-026/CONTRATO.md`."""

from __future__ import annotations

from typing import Any

from ._h026 import Mundo, emitir_noviembre, informar_y_confirmar, reimputar, revertir, ruta


def _partes(m: Mundo, pago: str) -> list[dict[str, Any]]:
    r = m.cliente.get(ruta(m, f"/{pago}"))
    assert r.status_code == 200, f"leer el pago: {r.status_code} {r.text[:300]}"
    partes = r.json()["partes"]
    for p in partes:
        assert {"unidad_vigente_id", "identificador_vigente"} <= set(p), f"la parte no trae la unidad vigente: {p}"
    return list(partes)


def _de_la_lista(m: Mundo, pago: str) -> list[dict[str, Any]]:
    r = m.cliente.get(ruta(m))
    assert r.status_code == 200, r.text[:300]
    (elegido,) = [p for p in r.json() if p["pago_id"] == pago]
    return list(elegido["partes"])


def test_c04_sin_reimputar_la_vigente_es_la_misma(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    (parte,) = _partes(mundo, pago)
    assert (parte["unidad_vigente_id"], parte["identificador_vigente"]) == (str(mundo.unidades["1A"]), "1A"), parte


def test_c04_reimputado_la_vigente_es_el_destino(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1B": "43350.00"}, numero="en-1b")
    assert reimputar(mundo, pago, "1B", "1A").status_code == 200
    (parte,) = _partes(mundo, pago)
    assert parte["unidad_id"] == str(mundo.unidades["1B"]), "la parte original no cambia"
    assert (parte["unidad_vigente_id"], parte["identificador_vigente"]) == (str(mundo.unidades["1A"]), "1A"), parte
    (de_la_lista,) = _de_la_lista(mundo, pago)
    assert de_la_lista["identificador_vigente"] == "1A", de_la_lista
    assert reimputar(mundo, pago, "1A", "2A", "Tampoco era de 1A").status_code == 200
    assert _partes(mundo, pago)[0]["identificador_vigente"] == "2A"


def test_c04_revertido_queda_la_ultima(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1B": "43350.00"}, numero="en-1b")
    assert reimputar(mundo, pago, "1B", "1A").status_code == 200
    assert revertir(mundo, pago).status_code == 200
    assert _partes(mundo, pago)[0]["identificador_vigente"] == "1A"
