"""H-020 · confirmar y rechazar (C01 a C07, N01 a N06). Contrato en `aceptacion/H-020/CONTRATO.md`."""

from __future__ import annotations

import importlib
from datetime import date
from typing import Any
from uuid import uuid4

import pytest

from ._h020 import (
    CBU,
    OCT,
    SEP,
    Mundo,
    auditorias,
    campo_422,
    conflicto_de_estado,
    confirmar,
    del_libro,
    emitir,
    emitir_noviembre,
    estado,
    eventos,
    filas_de,
    informar_ok,
    informar_y_confirmar,
    intereses_de_la_emision,
    listar,
    ok,
    pagos_del_libro,
    rechazar,
    residuales_por_periodo,
    ruta,
)


def _no_encontrado(r: Any) -> None:
    assert r.status_code == 404, f"se esperaba 404, llegó {r.status_code}: {r.text[:300]}"
    assert r.json() == {"detail": "no encontrado"}, r.json()


def _informado(m: Mundo, partes: dict[str, str], **kwargs: Any) -> str:
    m.como("ana" if set(partes) <= {"1A", "2B"} else "beto")
    pago = informar_ok(m, partes, **kwargs)
    m.como("admin_principal")
    return pago


# --- C01: confirmar imputa ------------------------------------------------------------------------


def test_c01_confirmar_imputa_el_pago(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00"})
    ok(confirmar(mundo, pago), "confirmado", pago)
    assert pagos_del_libro(mundo, "1A") == [("pago", "43350.00", date(2026, 11, 5))], pagos_del_libro(mundo, "1A")
    assert estado(mundo, "1A").deuda.a_texto() == "0.00"
    assert eventos(mundo, pago) == [("confirmado", None)], eventos(mundo, pago)
    papeles = mundo.filas("SELECT papel FROM movimiento_de_pago WHERE pago_id = %s", (pago,))
    assert [f[0] for f in papeles] == ["pago"], papeles
    assert auditorias(mundo, "confirmar_pago_informado") == 1
    assert {p["pago_id"]: p["estado"] for p in listar(mundo)}[pago] == "confirmado"


# --- C02 y C03: la fecha de la transferencia y R04 a esa fecha --------------------------------------


def _deuda_de_septiembre(m: Mundo) -> None:
    emitir(m, SEP, {"1A": "100000.00", "1B": "100000.00"})


def test_c02_confirmado_tarde_sin_interes_por_la_demora(mundo: Mundo) -> None:
    """Escenario: Confirmado tarde, sin interés por la demora"""
    _deuda_de_septiembre(mundo)
    emitir(mundo, OCT, {"1A": "1000.00", "1B": "1000.00"})
    informar_y_confirmar(mundo, {"1A": "100000.00"}, fecha="2026-09-30", numero="sep-1a")
    noviembre = emitir(mundo, date(2026, 11, 1), {"1A": "1000.00", "1B": "1000.00"})
    assert intereses_de_la_emision(mundo, "1A", noviembre) == "21.00", (
        "en noviembre 1A sólo debe el interés de octubre sobre $1.000 (21 días): el capital de septiembre se pagó "
        f"el 30/09 aunque se confirmó después; llegó {intereses_de_la_emision(mundo, '1A', noviembre)}"
    )


def test_c03_r04_a_la_fecha_de_la_transferencia(mundo: Mundo) -> None:
    _deuda_de_septiembre(mundo)
    informar_y_confirmar(mundo, {"1B": "100000.00"}, fecha="2026-09-30", numero="sep-1b")
    emitir(mundo, OCT, {"1A": "1000.00", "1B": "1000.00"})
    informar_y_confirmar(mundo, {"1A": "100000.00"}, fecha="2026-09-30", numero="sep-1a")
    emitir(mundo, date(2026, 11, 1), {"1A": "1000.00", "1B": "1000.00"})
    a, b = residuales_por_periodo(mundo, "1A"), residuales_por_periodo(mundo, "1B")
    assert a == b, f"1A (confirmado tarde) y 1B (confirmado a tiempo) tienen que quedar iguales: 1A {a}, 1B {b}"
    assert a[("2026-09-01", "ordinaria")] == "0.00", "el pago va primero al capital que existía el 30/09"
    assert a[("2026-09-01", "interes")] == "2000.00", "el interés de septiembre (emitido en octubre) sigue debido"
    assert estado(mundo, "1A").deuda == estado(mundo, "1B").deuda


# --- C04: excedente ----------------------------------------------------------------------------------


def test_c04_excedente(mundo: Mundo) -> None:
    """Escenario: Excedente"""
    emitir_noviembre(mundo)
    informar_y_confirmar(mundo, {"1A": "50000.00"})
    e = estado(mundo, "1A")
    assert (e.deuda.a_texto(), e.credito_a_favor_aplicable.a_texto()) == ("0.00", "6650.00"), (
        e.deuda.a_texto(), e.credito_a_favor_aplicable.a_texto())


# --- C05: reparto ------------------------------------------------------------------------------------


def test_c05_reparto(mundo: Mundo) -> None:
    """Escenario: Reparto"""
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00", "2B": "37425.00"})
    assert pagos_del_libro(mundo, "1A") == [("pago", "43350.00", date(2026, 11, 5))]
    assert pagos_del_libro(mundo, "2B") == [("pago", "37425.00", date(2026, 11, 5))]
    assert (estado(mundo, "1A").deuda.a_texto(), estado(mundo, "2B").deuda.a_texto()) == ("0.00", "0.00")
    assert len(mundo.filas("SELECT 1 FROM movimiento_de_pago WHERE pago_id = %s AND papel = 'pago'", (pago,))) == 2


# --- C06: el CBU de origen ---------------------------------------------------------------------------


def test_c06_el_cbu_queda_para_la_unidad(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"}, cbu=CBU)
    filas = mundo.filas("SELECT unidad_id, cbu, pago_id FROM cbu_de_unidad WHERE pago_id = %s", (pago,))
    assert [(str(f[0]), f[1], str(f[2])) for f in filas] == [(str(mundo.unidades["1A"]), CBU, pago)], filas


def test_c06_sin_cbu_no_guarda_nada(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    informar_y_confirmar(mundo, {"1A": "43350.00"})
    assert filas_de(mundo, "cbu_de_unidad") == 0


# --- C07: rechazar -------------------------------------------------------------------------------------


def test_c07_rechazo(mundo: Mundo) -> None:
    """Escenario: Rechazo"""
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00"})
    libro = del_libro(mundo)
    ok(rechazar(mundo, pago, "  El monto no coincide con el comprobante  "), "rechazado", pago)
    assert del_libro(mundo) == libro, "rechazar escribió en el libro"
    assert eventos(mundo, pago) == [("rechazado", "El monto no coincide con el comprobante")], eventos(mundo, pago)
    assert auditorias(mundo, "rechazar_pago_informado") == 1
    mundo.como("ana")
    visto = {p["pago_id"]: (p["estado"], p["motivo"]) for p in listar(mundo)}
    assert visto[pago] == ("rechazado", "El monto no coincide con el comprobante"), visto


# --- N01: confirmar dos veces --------------------------------------------------------------------------


def test_n01_confirmar_dos_veces_seguidas(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00", "2B": "37425.00"})
    ok(confirmar(mundo, pago), "confirmado", pago)
    ok(confirmar(mundo, pago), "confirmado", pago)
    assert len(pagos_del_libro(mundo, "1A")) == 1 and len(pagos_del_libro(mundo, "2B")) == 1
    assert eventos(mundo, pago) == [("confirmado", None)]
    assert auditorias(mundo, "confirmar_pago_informado") == 1


def test_n01_confirmar_en_carrera(mundo: Mundo) -> None:
    """Escenario: Doble clic"""
    from ._h020 import en_paralelo

    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00", "2B": "37425.00"})
    respuestas = en_paralelo(lambda: confirmar(mundo, pago), lambda: confirmar(mundo, pago))
    for r in respuestas:
        assert not isinstance(r, BaseException), f"una confirmación lanzó: {r!r}"
        ok(r, "confirmado", pago)
    assert len(pagos_del_libro(mundo, "1A")) == 1 and len(pagos_del_libro(mundo, "2B")) == 1
    assert eventos(mundo, pago) == [("confirmado", None)]


# --- N02: el estado manda --------------------------------------------------------------------------


def test_n02_confirmar_un_rechazado(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00"})
    ok(rechazar(mundo, pago), "rechazado", pago)
    conflicto_de_estado(confirmar(mundo, pago))
    conflicto_de_estado(rechazar(mundo, pago))
    assert pagos_del_libro(mundo, "1A") == []


def test_n02_rechazar_un_confirmado(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    conflicto_de_estado(rechazar(mundo, pago))
    assert eventos(mundo, pago) == [("confirmado", None)]


def test_n02_confirmar_un_revertido(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = informar_y_confirmar(mundo, {"1A": "43350.00"})
    mundo.ejecutar("INSERT INTO evento_de_pago (administracion_id, pago_id, tipo, motivo, registrado_por) "
                   "VALUES (%s, %s, 'revertido', 'Cheque rechazado', %s)",
                   (mundo.admin, pago, mundo.personas["super_admin"]))
    conflicto_de_estado(confirmar(mundo, pago))
    assert len(pagos_del_libro(mundo, "1A")) == 1


# --- N03: el motivo del rechazo ------------------------------------------------------------------------


@pytest.mark.parametrize("motivo", [None, "", "ab", "  ab  ", "x" * 501, 123])
def test_n03_rechazar_sin_motivo_valido(mundo: Mundo, motivo: Any) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00"})
    assert campo_422(rechazar(mundo, pago, motivo)) == "motivo"
    assert eventos(mundo, pago) == []


def test_n03_los_bordes_del_motivo_entran(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    ok(rechazar(mundo, pago := _informado(mundo, {"1A": "43350.00"}, numero="m3"), "abc"), "rechazado", pago)
    ok(rechazar(mundo, otro := _informado(mundo, {"1A": "43350.00"}, numero="m500"), "y" * 500), "rechazado", otro)


# --- N04: sin permiso ----------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["ana", "beto", "consejo", "contador", "auxiliar"])
def test_n04_sin_permiso(mundo: Mundo, rol: str) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00"})
    mundo.como(rol)
    for r in (confirmar(mundo, pago), rechazar(mundo, pago)):
        assert r.status_code == 403, f"{rol}: se esperaba 403, llegó {r.status_code}: {r.text[:200]}"
    assert eventos(mundo, pago) == [] and pagos_del_libro(mundo, "1A") == []


# --- N05: otro edificio u otra administración --------------------------------------------------------


def test_n05_pago_ajeno(mundo: Mundo) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00"})
    _no_encontrado(mundo.cliente.post(ruta(mundo, f"/{pago}/confirmacion", complejo=mundo.otro), json={}))
    _no_encontrado(confirmar(mundo, str(uuid4())))
    mundo.como("administracion_b")
    _no_encontrado(confirmar(mundo, pago))
    _no_encontrado(mundo.cliente.post(ruta(mundo, f"/{pago}/confirmacion", complejo=mundo.edificio_b), json={}))
    mundo.como("admin_de_otro_edificio")
    _no_encontrado(confirmar(mundo, pago))
    assert eventos(mundo, pago) == []


# --- N06: falla a mitad de camino --------------------------------------------------------------------


def test_n06_falla_a_mitad_no_deja_nada(mundo: Mundo, monkeypatch: pytest.MonkeyPatch) -> None:
    emitir_noviembre(mundo)
    pago = _informado(mundo, {"1A": "43350.00", "2B": "37425.00"}, cbu=CBU)
    try:
        libro = importlib.import_module("proptech_core.cuenta_corriente.aplicacion.pagos")
    except ImportError as error:
        raise AssertionError(f"falta `cuenta_corriente.aplicacion.pagos`: {error}") from None
    original = getattr(libro, "registrar_pago", None)
    assert original is not None, "falta `registrar_pago`"
    llamadas: list[int] = []

    def falla_en_la_segunda(*args: Any, **kwargs: Any) -> Any:
        llamadas.append(1)
        if len(llamadas) == 2:
            raise RuntimeError("falla inyectada en la segunda parte")
        return original(*args, **kwargs)

    monkeypatch.setattr(libro, "registrar_pago", falla_en_la_segunda)
    with pytest.raises(RuntimeError, match="falla inyectada"):
        confirmar(mundo, pago)
    assert len(llamadas) == 2, f"registrar_pago tiene que llamarse una vez por parte: {len(llamadas)} llamadas"
    assert pagos_del_libro(mundo, "1A") == [] and pagos_del_libro(mundo, "2B") == [], "quedó una parte imputada"
    assert eventos(mundo, pago) == [], "quedó el evento"
    assert filas_de(mundo, "cbu_de_unidad") == 0 and filas_de(mundo, "movimiento_de_pago") == 0
    assert auditorias(mundo, "confirmar_pago_informado") == 0
