"""H-042 · la marca de gestión judicial (C05 a C08). Contrato en `aceptacion/H-042/CONTRATO.md`."""

from __future__ import annotations

import psycopg
import pytest

from ._h042 import (
    CLAVES_DE_FILA,
    CORTE,
    HOY,
    Mundo,
    armar_la_deuda,
    auditorias,
    desmarcar_ok,
    emitir_certificado,
    fila_de,
    marcar_ok,
    marcas_del_historial,
    morosidad,
    sin_espacios,
    situacion,
    situaciones_del_edificio,
    texto_del_pdf,
    unidades_marcadas,
)

LEYENDA = "engestiónjudicial"

# --- C05: marcar y desmarcar, auditado y con su historial de sólo agregar ---------------------------------------------


def test_c05_marcar_guarda_la_marca_con_su_motivo_y_la_audita(mundo: Mundo) -> None:
    """Escenario: el super admin marca la `1A` el 18/11 porque pasó al estudio jurídico"""
    armar_la_deuda(mundo)
    m = marcar_ok(mundo, "1A", "Pasó al estudio jurídico del consorcio")
    assert (m["unidad_id"], m["en_gestion_judicial"], m["motivo"], m["fecha"]) == (
        str(mundo.unidades["1A"]), True, "Pasó al estudio jurídico del consorcio", "2026-11-18"), m
    (fila,) = marcas_del_historial(mundo)
    assert (str(fila[0]), fila[1], fila[2], fila[3], fila[4], fila[5]) == (
        m["id"], mundo.unidades["1A"], "marcar", "Pasó al estudio jurídico del consorcio", HOY,
        mundo.personas["super_admin"]), fila
    (aud,) = auditorias(mundo, "marcar_gestion_judicial")
    assert (aud[0], str(aud[1]), aud[2]) == ("gestion_judicial_de_unidad", m["id"], mundo.personas["super_admin"])
    assert aud[3] == {"unidad_id": str(mundo.unidades["1A"]), "motivo": "Pasó al estudio jurídico del consorcio"}, aud[3]


def test_c05_desmarcar_agrega_un_evento_y_lo_audita(mundo: Mundo) -> None:
    """Escenario: la `1A` se marca y después se desmarca con otro motivo"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "1A", "Pasó al estudio jurídico")
    d = desmarcar_ok(mundo, "1A", "Regularizó la deuda con un plan")
    assert (d["unidad_id"], d["en_gestion_judicial"], d["motivo"], d["fecha"]) == (
        str(mundo.unidades["1A"]), False, "Regularizó la deuda con un plan", "2026-11-18"), d
    filas = marcas_del_historial(mundo)
    assert [(f[2], f[3]) for f in filas] == [("marcar", "Pasó al estudio jurídico"),
                                            ("desmarcar", "Regularizó la deuda con un plan")], filas
    assert str(filas[1][0]) == d["id"] and filas[0][0] != filas[1][0]
    (aud,) = auditorias(mundo, "desmarcar_gestion_judicial")
    assert (aud[0], str(aud[1]), aud[2]) == ("gestion_judicial_de_unidad", d["id"], mundo.personas["super_admin"])
    assert aud[3] == {"unidad_id": str(mundo.unidades["1A"]), "motivo": "Regularizó la deuda con un plan"}, aud[3]
    assert len(auditorias(mundo, "marcar_gestion_judicial")) == 1, "cada evento, su fila"


def test_c05_el_historial_es_de_solo_agregar_y_acumula_cada_vuelta(mundo: Mundo) -> None:
    """Escenario: marcar, desmarcar y marcar de nuevo; la aplicación no puede cambiar ni borrar un evento"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "1A", "Primera vez")
    desmarcar_ok(mundo, "1A", "Primer cierre")
    marcar_ok(mundo, "1A", "Segunda vez")
    assert [(f[2], f[3]) for f in marcas_del_historial(mundo)] == [
        ("marcar", "Primera vez"), ("desmarcar", "Primer cierre"), ("marcar", "Segunda vez")]
    ids = [f[0] for f in marcas_del_historial(mundo)]
    with pytest.raises(psycopg.Error):
        mundo.ejecutar("UPDATE gestion_judicial_de_unidad SET motivo = 'otro' WHERE id = %s", (ids[0],))
    with pytest.raises(psycopg.Error):
        mundo.ejecutar("DELETE FROM gestion_judicial_de_unidad WHERE id = %s", (ids[1],))
    assert [f[0] for f in marcas_del_historial(mundo)] == ids
    assert marcas_del_historial(mundo)[0][3] == "Primera vez"


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal"])
def test_c05_el_super_admin_y_el_administrador_principal_marcan_y_desmarcan(mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} marca y desmarca la `2A`"""
    armar_la_deuda(mundo)
    mundo.como(rol)
    marcar_ok(mundo, "2A")
    desmarcar_ok(mundo, "2A")
    assert [(f[2], f[5]) for f in marcas_del_historial(mundo)] == [
        ("marcar", mundo.personas[rol]), ("desmarcar", mundo.personas[rol])]


# --- C06: la marca saca a la unidad del moroso crítico (R31, R20) -------------------------------------------------------


def test_c06_una_unidad_marcada_deja_de_ser_moroso_critico_en_situacion_de_cuenta_y_al_desmarcar_vuelve(
        mundo: Mundo) -> None:
    """Escenario: la `1A` tiene 2 liquidaciones vencidas al 05/11 y 3 al 18/11; se marca y se desmarca"""
    armar_la_deuda(mundo)
    antes = situacion(mundo, "1A", CORTE)
    assert (antes.etiqueta, antes.moroso_critico, antes.liquidaciones_vencidas) == ("moroso_critico", True, 2)
    marcar_ok(mundo, "1A")
    for fecha, vencidas in ((CORTE, 2), (HOY, 3)):
        s = situacion(mundo, "1A", fecha)
        assert (s.etiqueta, s.moroso_critico, s.liquidaciones_vencidas) == ("con_deuda_vencida", False, vencidas), (
            f"marcada, aunque tenga {vencidas} liquidaciones vencidas: {s}")
    assert situacion(mundo, "1A", CORTE).total_vencido == antes.total_vencido, "la marca no cambia lo que debe"
    desmarcar_ok(mundo, "1A")
    vuelta = situacion(mundo, "1A", CORTE)
    assert (vuelta.etiqueta, vuelta.moroso_critico) == ("moroso_critico", True), "desmarcada, vuelve (R31)"


def test_c06_lo_mismo_en_situacion_del_edificio_y_las_otras_unidades_no_cambian(mundo: Mundo) -> None:
    """Escenario: `1A`, `2A` y `2B` son morosos críticos al 05/11; se marca sólo la `1A`"""
    armar_la_deuda(mundo)
    etiquetas = {u: s.etiqueta for u, s in situaciones_del_edificio(mundo, CORTE).items()}
    assert etiquetas == {"1A": "moroso_critico", "1B": "sin_deuda_vencida", "2A": "moroso_critico",
                         "2B": "moroso_critico"}, etiquetas
    marcar_ok(mundo, "1A")
    marcada = {u: s.etiqueta for u, s in situaciones_del_edificio(mundo, CORTE).items()}
    assert marcada == {**etiquetas, "1A": "con_deuda_vencida"}, marcada
    desmarcar_ok(mundo, "1A")
    assert {u: s.etiqueta for u, s in situaciones_del_edificio(mundo, CORTE).items()} == etiquetas


def test_c06_la_morosidad_del_10a_no_cuenta_a_la_marcada_como_moroso_critico_y_al_desmarcar_vuelve(
        mundo: Mundo) -> None:
    """Escenario: el 18/11 la `1A` (30.720,00), la `2A` y la `2B` son morosos críticos; se marca la `1A`"""
    armar_la_deuda(mundo)
    antes = morosidad(mundo)
    assert antes["resumen"]["morosos_criticos"] == 3 and antes["unidades"][0]["unidad"] == "1A", antes["resumen"]
    marcar_ok(mundo, "1A")
    cuerpo = morosidad(mundo)
    assert cuerpo["resumen"]["morosos_criticos"] == 2, cuerpo["resumen"]
    assert cuerpo["resumen"]["unidades_con_deuda"] == antes["resumen"]["unidades_con_deuda"], "sigue debiendo"
    fila = fila_de(cuerpo, "1A")
    assert (fila["etiqueta"], fila["total_vencido"]) == ("con_deuda_vencida", fila_de(antes, "1A")["total_vencido"])
    assert [f["unidad"] for f in cuerpo["unidades"]][-1] == "1A", "los morosos críticos van primero"
    desmarcar_ok(mundo, "1A")
    vuelta = morosidad(mundo)
    assert [{k: v for k, v in f.items() if k != "en_gestion_judicial"} for f in vuelta["unidades"]] == antes["unidades"]
    assert vuelta["resumen"] == antes["resumen"]


def test_c06_una_unidad_marcada_con_deuda_de_intereses_conserva_esa_etiqueta(mundo: Mundo) -> None:
    """Escenario: la `1B` sólo debe 600,00 de interés al 05/11; marcarla no la vuelve `con_deuda_vencida`"""
    armar_la_deuda(mundo, b_tarde=True)
    marcar_ok(mundo, "1B")
    s = situacion(mundo, "1B", CORTE)
    assert (s.etiqueta, str(s.total_vencido)) == ("deuda_de_intereses", "600.00"), s
    assert situaciones_del_edificio(mundo, CORTE)["1A"].etiqueta == "moroso_critico", "las demás, igual"


# --- C07: la consulta para el 13 --------------------------------------------------------------------------------------


def test_c07_unidades_en_gestion_judicial_devuelve_las_marcadas_del_edificio(mundo: Mundo) -> None:
    """Escenario: se marcan la `1A` y la `1B` (que no debe nada), se desmarca la `1A` y se marca de nuevo"""
    armar_la_deuda(mundo)
    assert unidades_marcadas(mundo) == set(), "sin marcas, vacío"
    marcar_ok(mundo, "1A")
    marcar_ok(mundo, "1B")
    assert unidades_marcadas(mundo) == {mundo.unidades["1A"], mundo.unidades["1B"]}
    desmarcar_ok(mundo, "1A")
    assert unidades_marcadas(mundo) == {mundo.unidades["1B"]}, "desmarcada sale de la lista"
    marcar_ok(mundo, "1A")
    assert unidades_marcadas(mundo) == {mundo.unidades["1A"], mundo.unidades["1B"]}, "marcada de nuevo, vuelve"


def test_c07_la_consulta_es_por_edificio_y_no_ve_las_marcas_de_otra_administracion(mundo: Mundo) -> None:
    """Escenario: se marca una unidad del otro edificio y otra de la administración B"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "1A")
    r = mundo.cliente.post(f"/api/complejos/{mundo.otro}/unidades/{mundo.unidad_otro}/gestion-judicial",
                           json={"motivo": "Otro edificio"})
    assert r.status_code == 201, f"marcar en el otro edificio: {r.status_code} {r.text[:200]}"
    mundo.como("administracion_b")
    r = mundo.cliente.post(f"/api/complejos/{mundo.edificio_b}/unidades/{mundo.unidad_b}/gestion-judicial",
                           json={"motivo": "Administración B"})
    assert r.status_code == 201, f"marcar en la administración B: {r.status_code} {r.text[:200]}"
    mundo.como("super_admin")
    assert unidades_marcadas(mundo) == {mundo.unidades["1A"]}
    assert unidades_marcadas(mundo, mundo.otro) == {mundo.unidad_otro}
    assert unidades_marcadas(mundo, mundo.edificio_b) == set(), "otra administración: RLS"


# --- C08: la marca en la morosidad y en el certificado ----------------------------------------------------------------


def test_c08_la_morosidad_muestra_la_marca_en_la_fila_de_la_unidad(mundo: Mundo) -> None:
    """Escenario: se marca la `1A`; sólo su fila lleva `en_gestion_judicial: true`"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "1A")
    cuerpo = morosidad(mundo)
    marcada = fila_de(cuerpo, "1A")
    assert set(marcada) == CLAVES_DE_FILA | {"en_gestion_judicial"} and marcada["en_gestion_judicial"] is True, marcada
    for unidad in ("2A", "2B"):
        assert set(fila_de(cuerpo, unidad)) == CLAVES_DE_FILA, f"la {unidad} conserva las diez claves de H-027"
    desmarcar_ok(mundo, "1A")
    assert set(fila_de(morosidad(mundo), "1A")) == CLAVES_DE_FILA, "desmarcada, sin la marca"


def test_c08_el_certificado_de_una_unidad_marcada_lleva_la_marca_y_la_leyenda(mundo: Mundo) -> None:
    """Escenario: se emite el libre deuda de la `1A` antes y después de marcarla, y el de la `1B` sin marca"""
    armar_la_deuda(mundo)
    antes = emitir_certificado(mundo, "1A", CORTE)
    assert antes["en_gestion_judicial"] is False and LEYENDA not in sin_espacios(texto_del_pdf(mundo, antes)).lower()
    marcar_ok(mundo, "1A")
    despues = emitir_certificado(mundo, "1A", CORTE)
    assert despues["en_gestion_judicial"] is True, despues
    assert LEYENDA in sin_espacios(texto_del_pdf(mundo, despues)).lower(), "el PDF lleva la leyenda"
    assert LEYENDA not in sin_espacios(texto_del_pdf(mundo, antes)).lower(), "el ya emitido no cambia (mismo PDF)"
    lista = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/unidades/{mundo.unidades['1A']}/libre-deuda").json()
    assert {c["id"]: c["en_gestion_judicial"] for c in lista} == {antes["id"]: False, despues["id"]: True}
    sana = emitir_certificado(mundo, "1B", CORTE)
    assert sana["en_gestion_judicial"] is False and LEYENDA not in sin_espacios(texto_del_pdf(mundo, sana)).lower()
    desmarcar_ok(mundo, "1A")
    assert emitir_certificado(mundo, "1A", CORTE)["en_gestion_judicial"] is False, "desmarcada, sin marca"
