"""H-024 · el comprobante con link firmado y el control de pagos sin confirmar (C01 a C03, N01 a N03).

Contrato en `aceptacion/H-024/CONTRATO.md`. C04 (H-012 y H-015 siguen en verde) y C05 (la KB) los mide `aceptar.py`.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from ._h024 import (
    CLAVE_DE_ENLACES,
    JPEG,
    PDF,
    PNG,
    Mundo,
    confirmar,
    enlace,
    informar_con,
    preliquidacion,
    rechazar,
)


def _url(r: Any) -> str:
    assert r.status_code == 201, f"enlace: se esperaba 201, llegó {r.status_code}: {r.text[:300]}"
    datos = r.json()
    assert set(datos) == {"url", "vence_en"}, datos
    assert datos["url"].startswith("/api/comprobantes/descarga?token="), datos["url"]
    vence = datetime.fromisoformat(datos["vence_en"])
    assert vence.tzinfo is not None, "el vencimiento lleva zona horaria"
    falta = vence - datetime.now(UTC)
    assert timedelta(minutes=14) < falta <= timedelta(minutes=15, seconds=5), f"vence a los 15 minutos: {falta}"
    return str(datos["url"])


def _firmar(**datos: Any) -> str:
    try:
        modulo = importlib.import_module("proptech_core.pagos.aplicacion.enlaces")
    except ImportError as error:
        raise AssertionError(f"falta `pagos.aplicacion.enlaces`: {error}") from None
    funcion = getattr(modulo, "firmar_enlace_del_comprobante", None)
    assert funcion is not None, "falta `firmar_enlace_del_comprobante`"
    return str(funcion(**datos))


def _pago_de_ana(m: Mundo, contenido: bytes = PNG, numero: str = "c-1a") -> str:
    m.como("ana")
    return informar_con(m, contenido, {"1A": "43350.00"}, numero)


# --- C01: el administrador descarga ----------------------------------------------------------------


@pytest.mark.parametrize(("contenido", "tipo"), [(PNG, "image/png"), (JPEG, "image/jpeg"), (PDF, "application/pdf")],
                         ids=["png", "jpg", "pdf"])
def test_c01_el_administrador_descarga_los_mismos_bytes(mundo: Mundo, contenido: bytes, tipo: str) -> None:
    """Escenario: Descarga"""
    pago = _pago_de_ana(mundo, contenido)
    mundo.como("admin_principal")
    url = _url(enlace(mundo, pago))
    d = mundo.cliente.get(url)
    assert d.status_code == 200, f"descarga: {d.status_code} {d.text[:200]}"
    assert d.content == contenido, "la descarga no trae los bytes que se subieron"
    assert d.headers.get("content-type", "").startswith(tipo), d.headers.get("content-type")


# --- C02: el vecino, vencido y alterado ---------------------------------------------------------------


def test_c02_el_vecino_vencido_y_alterado(mundo: Mundo) -> None:
    pago = _pago_de_ana(mundo)
    url = _url(enlace(mundo, pago))
    assert mundo.cliente.get(url).status_code == 200, "Ana descarga el comprobante de su pago"
    token = url.split("token=", 1)[1]
    cambiado = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert mundo.cliente.get(f"/api/comprobantes/descarga?token={cambiado}").status_code == 403
    vencido = _firmar(administracion_id=mundo.admin, pago_id=UUID(pago),
                      vence_en=datetime.now(UTC) - timedelta(minutes=1), clave=CLAVE_DE_ENLACES)
    assert mundo.cliente.get(f"/api/comprobantes/descarga?token={vencido}").status_code == 410
    vigente = _firmar(administracion_id=mundo.admin, pago_id=UUID(pago),
                      vence_en=datetime.now(UTC) + timedelta(minutes=5), clave=CLAVE_DE_ENLACES)
    assert mundo.cliente.get(f"/api/comprobantes/descarga?token={vigente}").status_code == 200
    de_otra = _firmar(administracion_id=mundo.admin_b, pago_id=UUID(pago),
                      vence_en=datetime.now(UTC) + timedelta(minutes=5), clave=CLAVE_DE_ENLACES)
    assert mundo.cliente.get(f"/api/comprobantes/descarga?token={de_otra}").status_code == 403


# --- C03: el control de pagos sin confirmar ------------------------------------------------------------


def _control(cuerpo: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in cuerpo["controles"] if c["codigo"] == "pagos_sin_confirmar"]


def test_c03_pagos_sin_confirmar(mundo: Mundo) -> None:
    """Escenario: Pagos sin confirmar"""
    mundo.como("ana")
    uno = informar_con(mundo, PNG, {"1A": "30000.00"}, "p1")
    otro = informar_con(mundo, PNG, {"2B": "15000.00"}, "p2")
    mundo.como("admin_principal")
    controles = preliquidacion(mundo)["controles"]
    assert controles and controles[-1]["codigo"] == "pagos_sin_confirmar", f"tiene que ser el último: {controles}"
    assert controles[-1]["nivel"] == "advertencia"
    assert controles[-1]["detalle"] == {"cantidad": 2, "total": "45000.00"}, controles[-1]
    assert confirmar(mundo, uno).status_code == 200
    assert _control(preliquidacion(mundo))[0]["detalle"] == {"cantidad": 1, "total": "15000.00"}
    assert rechazar(mundo, otro).status_code == 200
    assert _control(preliquidacion(mundo)) == [], "sin pagos informados el control no aparece"


def test_c03_sin_pagos_no_aparece(mundo: Mundo) -> None:
    mundo.como("admin_principal")
    assert _control(preliquidacion(mundo)) == []


# --- N01: un tipo de enlace no sirve para el otro ---------------------------------------------------------


def test_n01_un_token_de_expensa_no_baja_un_comprobante(mundo: Mundo) -> None:
    """Escenario: Un token de expensa no sirve para un comprobante"""
    from proptech_core.liquidacion.aplicacion.enlaces import firmar_enlace

    pago = _pago_de_ana(mundo)
    de_expensa = firmar_enlace(administracion_id=mundo.admin, documento_id=UUID(pago), variante="completa",
                               vence_en=datetime.now(UTC) + timedelta(minutes=5), clave=CLAVE_DE_ENLACES)
    assert mundo.cliente.get(f"/api/comprobantes/descarga?token={de_expensa}").status_code == 403
    de_comprobante = _url(enlace(mundo, pago)).split("token=", 1)[1]
    r = mundo.cliente.get(f"/api/documentos/descarga?token={de_comprobante}")
    assert r.status_code == 403, f"un token de comprobante no baja una expensa: {r.status_code}"


# --- N02: quién no puede pedir el enlace ----------------------------------------------------------------


@pytest.mark.parametrize(("rol", "codigo"), [("beto", 404), ("administracion_b", 404), ("admin_de_otro_edificio", 404),
                                              ("consejo", 403), ("contador", 403)])
def test_n02_quien_no_puede(mundo: Mundo, rol: str, codigo: int) -> None:
    pago = _pago_de_ana(mundo)
    mundo.como(rol)
    r = enlace(mundo, pago)
    assert r.status_code == codigo, f"{rol}: se esperaba {codigo}, llegó {r.status_code}: {r.text[:200]}"
    if codigo == 404:
        assert r.json() == {"detail": "no encontrado"}, f"un 404 de una ruta que existe: {r.json()}"


# --- N03: sin token no hay comprobante ----------------------------------------------------------------


def test_n03_sin_token_no_baja(mundo: Mundo) -> None:
    pago = _pago_de_ana(mundo)
    for url in ("/api/comprobantes/descarga", "/api/comprobantes/descarga?token=", f"/api/comprobantes/{pago}",
                f"/api/complejos/{mundo.edificio}/pagos/{pago}/comprobante"):
        r = mundo.cliente.get(url)
        assert r.status_code != 200 and PNG not in r.content, f"{url} devolvió el comprobante sin un token válido"
    r = mundo.cliente.get("/api/comprobantes/descarga?token=")
    assert r.status_code in (403, 422), f"un token vacío: {r.status_code}"
