"""H-015 · el PDF de la expensa y los enlaces firmados (C01 a C07, N01 a N04)."""

from __future__ import annotations

import hashlib
import importlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ._h015 import (
    CLAVE_DE_ENLACES,
    NOV,
    ColaFalsa,
    Mundo,
    agregar_vecinos,
    cargar_base,
    configurar,
    descargar,
    documento,
    documentos,
    emitir_lo_revisado,
    enlace,
    generar,
    generar_todos,
    pdf_de,
    reprocesar,
    texto_del_pdf,
)


def _emitida(m: Mundo) -> str:
    cargar_base(m)
    return str(emitir_lo_revisado(m)["liquidacion_id"])


# --- C01 a C04: generar, contenido, cola caída y reproceso -----------------------------------------


def test_c01_al_emitir_quedan_pendientes_y_se_generan(mundo: Mundo) -> None:
    """Escenario: Documentos de una emisión"""
    liquidacion = _emitida(mundo)
    lista = documentos(mundo, liquidacion)
    assert [(d["identificador"], d["variante"]) for d in lista] == [
        (u, v) for u in ("1A", "1B", "2A", "2B") for v in ("completa", "sin_extraordinaria")
    ], lista
    assert {d["estado"] for d in lista} == {"pendiente"}
    generar_todos(mundo, liquidacion)
    assert {d["estado"] for d in documentos(mundo, liquidacion)} == {"generado"}


def test_c01_la_tarea_del_worker_pasa_por_el_corte() -> None:
    """Lectura del código (importar `proptech_worker.ajustes` exige la configuración de la base)."""
    import re
    from pathlib import Path

    worker = Path(__file__).resolve().parents[3] / "src" / "proptech_worker"
    ajustes = (worker / "ajustes.py").read_text()
    assert "generar_pdf_de_expensa" in ajustes, "la tarea no está registrada en `AjustesDelWorker`"
    assert re.search(r"^\s*cron_jobs\s*=", ajustes, flags=re.M), "falta el barrido periódico (`cron_jobs`)"
    definicion = [p for p in worker.glob("*.py")
                  if re.search(r"def generar_pdf_de_expensa\b", p.read_text())]
    assert len(definicion) == 1, f"no se encuentra dónde se define la tarea: {definicion}"
    assert "ejecutar_con_corte" in definicion[0].read_text(), (
        "la tarea del PDF tiene que pasar por `ejecutar_con_corte` (H-016)"
    )


def test_c02_el_pdf_completo_de_1b(mundo: Mundo) -> None:
    """Escenario: Lo que dice la expensa"""
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    lista = documentos(mundo, liquidacion)
    texto = texto_del_pdf(pdf_de(mundo, documento(lista, "1B", "completa")["documento_id"], "completa"))
    for esperado in ("Torre Ficticia", "1B", "TF-1B", "noviembre de 2026", "10/11/2026", "Ordinaria",
                     "Extraordinaria", "Limpieza", "Ascensor", "Pintura", "Multa", "5.000,00", "27.000,00",
                     "1.350,00", "15.000,00", "48.350,00", "Saldo anterior"):
        assert esperado in texto, f"el PDF de 1B no dice «{esperado}»: {texto[:600]}"


def test_c02_la_variante_sin_extraordinaria(mundo: Mundo) -> None:
    """Escenario: La expensa del inquilino"""
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    lista = documentos(mundo, liquidacion)
    variante = documento(lista, "1B", "sin_extraordinaria")["documento_id"]
    texto = texto_del_pdf(pdf_de(mundo, variante, "sin_extraordinaria"))
    assert "33.350,00" in texto and "TF-1B" in texto, texto[:600]
    for ausente in ("Pintura", "15.000,00", "48.350,00"):
        assert ausente not in texto, f"la variante del inquilino muestra «{ausente}»"


def test_c03_sin_redis_la_emision_sale_y_el_reproceso_encola(mundo: Mundo) -> None:
    """Escenario: Redis caído al emitir"""
    mundo.app.state.cola = ColaFalsa(falla=True)
    liquidacion = _emitida(mundo)
    assert {d["estado"] for d in documentos(mundo, liquidacion)} == {"pendiente"}
    cola = ColaFalsa()
    mundo.app.state.cola = cola
    r = reprocesar(mundo, liquidacion)
    assert r.status_code == 202 and r.json() == {"encolados": 8}, f"{r.status_code} {r.text[:200]}"
    assert [t for t, _ in cola.llamadas] == ["generar_pdf_de_expensa"] * 8, cola.llamadas


def test_c03_con_la_cola_caida_el_reproceso_da_503(mundo: Mundo) -> None:
    liquidacion = _emitida(mundo)
    mundo.app.state.cola = ColaFalsa(falla=True)
    r = reprocesar(mundo, liquidacion)
    assert r.status_code == 503, f"{r.status_code} {r.text[:200]}"
    assert {d["estado"] for d in documentos(mundo, liquidacion)} == {"pendiente"}


def test_c04_un_fallo_queda_fallido_y_el_reproceso_lo_arregla(mundo: Mundo) -> None:
    """Escenario: Generación que falla"""
    liquidacion = _emitida(mundo)
    objetivo = documento(documentos(mundo, liquidacion), "1A", "completa")["documento_id"]

    def roto(_html: str) -> bytes:
        raise RuntimeError("sin fuentes")

    generar(mundo, objetivo, renderizar=roto)
    d = documento(documentos(mundo, liquidacion), "1A", "completa")
    assert d["estado"] == "fallido" and d["motivo"], d
    mundo.app.state.cola = ColaFalsa()
    assert reprocesar(mundo, liquidacion).status_code == 202
    assert documento(documentos(mundo, liquidacion), "1A", "completa")["estado"] == "pendiente"
    generar(mundo, objetivo)
    assert documento(documentos(mundo, liquidacion), "1A", "completa")["estado"] == "generado"


# --- C05 a C07: enlaces, variantes y archivo -------------------------------------------------------


def test_c05_enlace_vencido_y_alterado(mundo: Mundo) -> None:
    """Escenario: Enlace firmado"""
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    objetivo = documento(documentos(mundo, liquidacion), "1A", "completa")["documento_id"]
    r = enlace(mundo, objetivo, "completa")
    assert r.status_code == 201, r.text[:300]
    cuerpo = r.json()
    vence = datetime.fromisoformat(cuerpo["vence_en"].replace("Z", "+00:00"))
    assert timedelta(minutes=10) < vence - datetime.now(UTC) <= timedelta(minutes=16), cuerpo["vence_en"]
    assert descargar(mundo, cuerpo["url"]).status_code == 200
    alterado = cuerpo["url"][:-1] + ("A" if cuerpo["url"][-1] != "A" else "B")
    assert descargar(mundo, alterado).status_code == 403
    firmar = getattr(importlib.import_module("proptech_core.liquidacion.aplicacion.enlaces"), "firmar_enlace")
    vencido = firmar(administracion_id=mundo.admin, documento_id=UUID(objetivo), variante="completa",
                     vence_en=datetime.now(UTC) - timedelta(minutes=1), clave=CLAVE_DE_ENLACES)
    assert descargar(mundo, f"/api/documentos/descarga?token={vencido}").status_code == 410


def test_c06_propietario_e_inquilino(mundo: Mundo) -> None:
    """Escenario: Quién descarga qué"""
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    agregar_vecinos(mundo)
    lista = documentos(mundo, liquidacion)
    completa = documento(lista, "1B", "completa")["documento_id"]
    sin_extra = documento(lista, "1B", "sin_extraordinaria")["documento_id"]
    mundo.como("propietario_1b")
    assert enlace(mundo, completa, "completa").status_code == 201
    assert enlace(mundo, sin_extra, "sin_extraordinaria").status_code == 201
    mundo.como("inquilino_1b")
    assert enlace(mundo, sin_extra, "sin_extraordinaria").status_code == 201
    r = enlace(mundo, completa, "completa")
    assert r.status_code == 403, f"el inquilino no recibe la completa: {r.status_code} {r.text[:200]}"


def test_c07_un_pdf_generado_no_cambia(mundo: Mundo) -> None:
    """Escenario: El PDF archivado no se reescribe"""
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    objetivo = documento(documentos(mundo, liquidacion), "1A", "completa")["documento_id"]
    antes = hashlib.sha256(pdf_de(mundo, objetivo, "completa")).hexdigest()
    mundo.ejecutar("UPDATE categoria_de_gasto SET nombre = 'Otra' WHERE id = %s", (mundo.categorias["Limpieza"],))
    configurar(mundo, fondo="10.00", desde=NOV)
    generar(mundo, objetivo)
    mundo.app.state.cola = ColaFalsa()
    reprocesar(mundo, liquidacion)
    assert hashlib.sha256(pdf_de(mundo, objetivo, "completa")).hexdigest() == antes


# --- N01 a N04 ------------------------------------------------------------------------------------


def test_n01_sin_token_no_hay_pdf(mundo: Mundo) -> None:
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    for url in ("/api/documentos/descarga", "/api/documentos/descarga?token="):
        r = descargar(mundo, url)
        assert r.status_code in (403, 422) and not r.content.startswith(b"%PDF"), f"{url}: {r.status_code}"
    assert all("contenido" not in d and "pdf" not in d for d in documentos(mundo, liquidacion))


def test_n02_el_inquilino_no_consigue_la_completa(mundo: Mundo) -> None:
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    agregar_vecinos(mundo)
    completa = documento(documentos(mundo, liquidacion), "1B", "completa")["documento_id"]
    mundo.como("inquilino_1b")
    assert enlace(mundo, completa, "sin_extraordinaria").status_code in (403, 422), (
        "pedir la completa con otra variante en el cuerpo no puede servir"
    )
    assert enlace(mundo, completa, "completa").status_code == 403


def test_n03_generar_otra_vez_no_duplica(mundo: Mundo) -> None:
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    generar_todos(mundo, liquidacion)
    lista = documentos(mundo, liquidacion)
    assert len(lista) == 8 and {d["estado"] for d in lista} == {"generado"}


def test_n04_un_vecino_de_otra_unidad_no_consigue_nada(mundo: Mundo) -> None:
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    agregar_vecinos(mundo)
    completa = documento(documentos(mundo, liquidacion), "1B", "completa")["documento_id"]
    mundo.como("propietario_2a")
    assert enlace(mundo, completa, "completa").status_code == 404


def test_n04_un_documento_pendiente_no_da_enlace(mundo: Mundo) -> None:
    liquidacion = _emitida(mundo)
    objetivo = documento(documentos(mundo, liquidacion), "1A", "completa")["documento_id"]
    r = enlace(mundo, objetivo, "completa")
    assert r.status_code == 409 and r.json().get("motivo") == "no_generado", f"{r.status_code} {r.text[:200]}"


@pytest.mark.parametrize("rol", ["auxiliar"])
def test_n04_sin_permiso_no_hay_enlace(mundo: Mundo, rol: str) -> None:
    liquidacion = _emitida(mundo)
    generar_todos(mundo, liquidacion)
    objetivo = documento(documentos(mundo, liquidacion), "1A", "completa")["documento_id"]
    mundo.como(rol)
    assert enlace(mundo, objetivo, "completa").status_code == 403
