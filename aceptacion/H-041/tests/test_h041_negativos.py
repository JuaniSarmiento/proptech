"""H-041 · lo que no tiene que pasar (N01 a N04). Contrato en `aceptacion/H-041/CONTRATO.md`."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import psycopg
import pytest

from ._h041 import (
    CORTE,
    HOY,
    Mundo,
    ars,
    armar_la_deuda,
    auditorias,
    bajar_el_pdf,
    cargo_sin_liquidar,
    del_libro,
    del_libro_a,
    emitir_certificado,
    filas_de_certificados,
    listar,
    no_encontrado,
    pedir,
    ruta,
    sin_permiso,
    texto_de,
    texto_del_pdf,
    verificar_forma,
)

SIN_PERMISO = ["admin_principal", "admin_del_edificio", "contador", "auxiliar", "consejo", "ana"]


# --- N01: sólo el super admin; lo ajeno no existe ----------------------------------------------------------------


@pytest.mark.parametrize("rol", SIN_PERMISO)
def test_n01_fuera_del_super_admin_emitir_da_403_y_no_guarda_nada(mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} intenta emitir el libre deuda de la `1A`"""
    armar_la_deuda(mundo)
    assert emitir_certificado(mundo, "1A", CORTE)["saldo"] == "20720.00", "control: el super admin emite"
    antes, auditadas = filas_de_certificados(mundo), len(auditorias(mundo))
    mundo.como(rol)
    sin_permiso(pedir(mundo, "1A", CORTE), f"POST como {rol}")
    assert (filas_de_certificados(mundo), len(auditorias(mundo))) == (antes, auditadas), "nada se guardó ni auditó"


@pytest.mark.parametrize("rol", SIN_PERMISO)
def test_n01_fuera_del_super_admin_listar_tambien_da_403(mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} pide la lista de certificados de la `1A`"""
    armar_la_deuda(mundo)
    emitir_certificado(mundo, "1A", CORTE)
    mundo.como(rol)
    sin_permiso(mundo.cliente.get(ruta(mundo, "1A")), f"GET como {rol}")


def test_n01_una_unidad_de_otro_edificio_o_de_otra_administracion_da_404(mundo: Mundo) -> None:
    """Escenario: el super admin con la `9A` del otro edificio; una persona de B con la `1A` de A"""
    armar_la_deuda(mundo)
    assert emitir_certificado(mundo, "1A", CORTE)["id"], "control: la propia responde"
    no_encontrado(pedir(mundo, mundo.unidad_otro, CORTE), "la 9A por el edificio de la 1A")
    no_encontrado(pedir(mundo, mundo.unidad_b, CORTE), "una unidad de la administración B")
    no_encontrado(pedir(mundo, uuid4(), CORTE), "una unidad inexistente")
    no_encontrado(mundo.cliente.get(ruta(mundo, mundo.unidad_otro)), "listar la 9A por el edificio de la 1A")
    mundo.como("admin_de_otro_edificio")
    no_encontrado(pedir(mundo, "1A", CORTE), "un administrador de otro edificio (el alcance va antes que el permiso)")
    mundo.como("administracion_b")
    no_encontrado(pedir(mundo, "1A", CORTE), "la 1A desde la administración B")
    no_encontrado(mundo.cliente.get(ruta(mundo, "1A")), "listar la 1A desde la administración B")
    assert filas_de_certificados(mundo) == 1, "sólo quedó el del control"


# --- N02: la fecha de corte ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("corte", ["2026-11-19", "2027-01-01"])
def test_n02_una_fecha_de_corte_futura_da_422_y_no_guarda_nada(mundo: Mundo, corte: str) -> None:
    """Escenario: hoy es el 18/11/2026 y se pide un corte posterior"""
    armar_la_deuda(mundo)
    r = pedir(mundo, "1A", corte)
    assert r.status_code == 422, f"se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
    assert (filas_de_certificados(mundo), auditorias(mundo)) == (0, []), "un pedido inválido no deja rastro"


def test_n02_el_corte_de_hoy_se_acepta_y_uno_pasado_tambien(mundo: Mundo) -> None:
    """Escenario: el borde es hoy; el pasado se emite con lo que el libro sabía a esa fecha"""
    armar_la_deuda(mundo)
    assert emitir_certificado(mundo, "1A", HOY)["fecha_de_corte"] == "2026-11-18"
    assert emitir_certificado(mundo, "1A", date(2026, 9, 30))["saldo"] == "10200.00"


@pytest.mark.parametrize("cuerpo", [{}, {"fecha_de_corte": None}, {"fecha_de_corte": "05/11/2026"},
                                    {"fecha_de_corte": "no es una fecha"}, {"fecha_de_corte": "2026-02-30"}])
def test_n02_un_cuerpo_sin_fecha_o_con_una_fecha_invalida_da_422(mundo: Mundo, cuerpo: dict[str, object]) -> None:
    """Escenario: cuerpos que no son una fecha ISO"""
    armar_la_deuda(mundo)
    r = mundo.cliente.post(ruta(mundo, "1A"), json=cuerpo)
    assert r.status_code == 422, f"{cuerpo}: se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
    assert filas_de_certificados(mundo) == 0


# --- N03: emitir no escribe en el libro; los certificados son de sólo agregar ----------------------------------------


def test_n03_emitir_dos_veces_con_el_mismo_corte_da_el_mismo_saldo_y_la_misma_huella(mundo: Mundo) -> None:
    """Escenario: el super admin vuelve a emitir el libre deuda de la `1A` al 05/11 sin que el libro cambie"""
    armar_la_deuda(mundo)
    uno = emitir_certificado(mundo, "1A", CORTE)
    dos = emitir_certificado(mundo, "1A", CORTE)
    assert uno["id"] != dos["id"], "emitir de nuevo crea otro certificado, con otro identificador (D-172)"
    assert (uno["saldo"], uno["capital"], uno["intereses"], uno["huella"]) == (
        dos["saldo"], dos["capital"], dos["intereses"], dos["huella"]), (uno, dos)
    assert filas_de_certificados(mundo) == 2 and len(auditorias(mundo)) == 2
    assert {c["id"] for c in listar(mundo, "1A")} == {uno["id"], dos["id"]}
    assert len({uno["huella"], emitir_certificado(mundo, "1A", date(2026, 11, 15))["huella"],
                emitir_certificado(mundo, "1B", CORTE)["huella"]}) == 3, "la huella depende del contenido"


def test_n03_emitir_no_escribe_en_el_libro(mundo: Mundo) -> None:
    """Escenario: tres certificados no mueven ni una fila de movimiento, imputación, obligación o cuenta"""
    armar_la_deuda(mundo)
    antes = del_libro(mundo)
    emitir_certificado(mundo, "1A", CORTE)
    emitir_certificado(mundo, "2B", date(2026, 11, 15))
    emitir_certificado(mundo, "1B", HOY)
    assert del_libro(mundo) == antes, "el libro quedó igual"


def test_n03_la_tabla_de_certificados_es_de_solo_agregar(mundo: Mundo) -> None:
    """Escenario: la aplicación intenta cambiar o borrar un certificado emitido"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert filas_de_certificados(mundo) == 1
    with pytest.raises(psycopg.Error):
        mundo.ejecutar("UPDATE certificado_de_libre_deuda SET saldo = 0 WHERE id = %s", (c["id"],))
    with pytest.raises(psycopg.Error):
        mundo.ejecutar("DELETE FROM certificado_de_libre_deuda WHERE id = %s", (c["id"],))
    assert filas_de_certificados(mundo) == 1 and emitir_certificado(mundo, "1A", CORTE)["saldo"] == "20720.00"
    assert mundo.uno("SELECT saldo::text FROM certificado_de_libre_deuda WHERE id = %s", (c["id"],)) == "20720.00"


# --- N04: nunca estima ---------------------------------------------------------------------------------------------------


def test_n04_el_certificado_no_suma_un_cargo_aprobado_que_todavia_no_se_liquido(mundo: Mundo) -> None:
    """Escenario: la `1A` tiene un cargo particular aprobado de 4.321,00 en noviembre sin liquidar"""
    armar_la_deuda(mundo)
    cargo_sin_liquidar(mundo, "1A", "4321.00")
    c = emitir_certificado(mundo, "1A", HOY)
    assert c["saldo"] == "30720.00" == texto_de(del_libro_a(mundo, "1A", HOY)["saldo"]), c
    assert c["vencen_despues"] == [], "el cargo no es una cuota del libro: tampoco se lista"
    assert ars("4321.00") not in texto_del_pdf(bajar_el_pdf(mundo, c))
    assert "4321.00" not in str(c) and set(verificar_forma(c)) == set(c), "ni una clave de estimación"


def test_n04_el_interes_corrido_no_entra_ni_en_el_saldo_ni_en_los_intereses_registrados(mundo: Mundo) -> None:
    """Escenario: octubre sigue impago el 18/11 pero el interés de noviembre todavía no se registró (C08 lo informa
    aparte)"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", HOY)
    assert (c["capital"], c["intereses"]) == ("30000.00", "720.00"), "sólo el registrado hasta el 31/10"
    assert c["intereses"] == texto_de(del_libro_a(mundo, "1A", HOY)["intereses"])
