"""H-039 · la distribución al abrir (C04). Contrato en `aceptacion/H-039/CONTRATO.md`."""

from __future__ import annotations

from ._h039 import (
    Mundo,
    base_dos_meses,
    como_admin,
    conteo_de_todo,
    del_administrador,
    detalle_ok,
    distribuciones,
    lista_ok,
)


def test_c04_la_primera_lectura_del_detalle_distribuye(mundo: Mundo) -> None:
    """Escenario: Ana abre noviembre de su `1A`; el administrador ya la ve distribuida por el portal"""
    meses = base_dos_meses(mundo)
    antes = del_administrador(mundo, meses.liq_nov)
    assert (antes["estado"], antes["distribucion"]) == ("emitida", None), "control: emitida y sin distribuir"
    mundo.como("ana")
    detalle_ok(mundo, "1A", meses.liq_nov)
    despues = del_administrador(mundo, meses.liq_nov)
    assert despues["estado"] == "distribuida", despues["estado"]
    assert despues["distribucion"]["origen"] == "portal", despues["distribucion"]
    eventos = distribuciones(mundo, str(meses.noviembre["emision_id"]))
    assert [e[0] for e in eventos] == ["portal"], eventos


def test_c04_distribuida_ya_no_se_anula(mundo: Mundo) -> None:
    """Escenario: después de que Ana la abrió, el administrador no puede anularla (R08, D-016)"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    detalle_ok(mundo, "1A", meses.liq_nov)
    r = como_admin(mundo, lambda: mundo.cliente.post(
        f"/api/complejos/{mundo.edificio}/liquidaciones/{meses.liq_nov}/anulacion", json={"motivo": "Un error"}))
    assert r.status_code == 409, f"se esperaba 409, llegó {r.status_code}: {r.text[:300]}"
    assert r.json().get("motivo") == "ya_distribuida", r.json()


def test_c04_las_siguientes_lecturas_no_repiten_el_efecto(mundo: Mundo) -> None:
    """Escenario: Ana la vuelve a abrir, y Dora (otra unidad) también"""
    meses = base_dos_meses(mundo)
    emision = str(meses.noviembre["emision_id"])
    mundo.como("ana")
    detalle_ok(mundo, "1A", meses.liq_nov)
    primera = distribuciones(mundo, emision)
    assert len(primera) == 1, primera
    foto = conteo_de_todo(mundo)
    detalle_ok(mundo, "1A", meses.liq_nov)
    detalle_ok(mundo, "2B", meses.liq_nov)
    mundo.como("dora")
    detalle_ok(mundo, "2A", meses.liq_nov)
    assert distribuciones(mundo, emision) == primera, "el primero gana: ni otro evento ni otro instante ni otra persona"
    assert conteo_de_todo(mundo) == foto, "releer no escribe nada en ninguna tabla"
    assert del_administrador(mundo, meses.liq_nov)["distribucion"]["origen"] == "portal"


def test_c04_el_detalle_de_otro_mes_distribuye_solo_ese_mes(mundo: Mundo) -> None:
    """Escenario: Ana abre octubre; noviembre sigue sin distribuir"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    detalle_ok(mundo, "1A", meses.liq_oct)
    assert del_administrador(mundo, meses.liq_oct)["estado"] == "distribuida"
    assert del_administrador(mundo, meses.liq_nov)["estado"] == "emitida", "noviembre no se tocó"


def test_c04_una_distribuida_a_mano_conserva_su_origen(mundo: Mundo) -> None:
    """Escenario: el administrador distribuyó noviembre; Ana la abre y el origen sigue siendo `manual`"""
    meses = base_dos_meses(mundo)
    r = mundo.cliente.post(f"/api/complejos/{mundo.edificio}/liquidaciones/{meses.liq_nov}/distribucion")
    assert r.status_code == 200, f"distribuir a mano: {r.status_code}: {r.text[:300]}"
    mundo.como("ana")
    detalle_ok(mundo, "1A", meses.liq_nov)
    assert [e[0] for e in distribuciones(mundo, str(meses.noviembre["emision_id"]))] == ["manual"]


def test_c04_la_lista_no_distribuye_y_el_detalle_solo_toca_la_distribucion(mundo: Mundo) -> None:
    """Escenario: listar no es abrir; abrir sólo agrega el evento de distribución (y a lo sumo su auditoría)"""
    meses = base_dos_meses(mundo)
    mundo.como("ana")
    foto = conteo_de_todo(mundo)
    lista_ok(mundo, "1A")
    assert conteo_de_todo(mundo) == foto, "listar no escribe nada"
    assert del_administrador(mundo, meses.liq_nov)["estado"] == "emitida", "listar no distribuye"
    mundo.como("ana")
    foto = conteo_de_todo(mundo)
    detalle_ok(mundo, "1A", meses.liq_nov)
    despues = conteo_de_todo(mundo)
    cambiadas = {t for t in foto if foto[t] != despues[t]}
    assert "evento_de_emision" in cambiadas, "la primera lectura distribuye"
    assert cambiadas <= {"evento_de_emision", "auditoria"}, f"sólo la distribución: cambiaron {sorted(cambiadas)}"
