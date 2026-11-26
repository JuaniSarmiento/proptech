"""H-042 · lo que no tiene que pasar (N01 a N04). Contrato en `aceptacion/H-042/CONTRATO.md`."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

import pytest

from ._h042 import (
    HOY,
    NOV,
    OCT,
    SEP,
    Mundo,
    armar_la_deuda,
    auditorias,
    condonaciones_del_edificio,
    condonaciones_del_libro,
    condonar,
    condonar_ok,
    cuerpo_de_condonacion,
    del_libro,
    desmarcar,
    desmarcar_ok,
    emitir_certificado,
    intereses_pendientes,
    interes_corrido_del_libro,
    marcar,
    marcar_ok,
    marcas_del_historial,
    no_encontrado,
    obligacion_de,
    pagar,
    saldo_de,
    sin_cambios,
    sin_permiso,
)

SIN_PERMISO = ["admin_del_edificio", "contador", "auxiliar", "consejo", "ana"]
MOTIVO_LARGO = "x" * 501


# --- N01: la condonación mal pedida da 422 sin cambios ---------------------------------------------------------------


def test_n01_un_cuerpo_invalido_da_422_y_no_cambia_nada(mundo: Mundo) -> None:
    """Escenario: motivo, importe u obligación mal formados, o un campo que no es del pedido (como el componente)"""
    armar_la_deuda(mundo)
    sep = str(obligacion_de(mundo, "1A", SEP))
    antes, saldo = del_libro(mundo), saldo_de(mundo, "1A")
    casos: dict[str, dict[str, Any]] = {
        "sin motivo": {"obligacion_id": sep, "importe": "100.00"},
        "motivo nulo": cuerpo_de_condonacion(sep, motivo=None),
        "motivo vacío": cuerpo_de_condonacion(sep, motivo=""),
        "motivo en blanco": cuerpo_de_condonacion(sep, motivo="   "),
        "motivo de 501": cuerpo_de_condonacion(sep, motivo=MOTIVO_LARGO),
        "motivo numérico": cuerpo_de_condonacion(sep, motivo=123),
        "sin importe": {"obligacion_id": sep, "motivo": "Motivo"},
        "importe nulo": cuerpo_de_condonacion(sep, importe=None),
        "importe cero": cuerpo_de_condonacion(sep, importe="0.00"),
        "importe negativo": cuerpo_de_condonacion(sep, importe="-5.00"),
        "importe que no es número": cuerpo_de_condonacion(sep, importe="abc"),
        "importe numérico": cuerpo_de_condonacion(sep, importe=10.5),
        "importe con tres decimales": cuerpo_de_condonacion(sep, importe="10.123"),
        "sin obligación": {"importe": "100.00", "motivo": "Motivo"},
        "obligación que no es un uuid": cuerpo_de_condonacion("no-es-un-uuid"),
        "el componente a condonar": {**cuerpo_de_condonacion(sep), "componente": "ordinaria"},
        "una unidad en el cuerpo": {**cuerpo_de_condonacion(sep), "unidad_id": str(mundo.unidades["1B"])},
        "motivo inválido y obligación inexistente (el 422 va antes)": cuerpo_de_condonacion(uuid4(), motivo=""),
    }
    for nombre, cuerpo in casos.items():
        r = condonar(mundo, "1A", cuerpo)
        assert r.status_code == 422, f"{nombre}: se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
        sin_cambios(mundo, antes, 0, "condonar_intereses", nombre)
    assert saldo_de(mundo, "1A") == saldo and condonaciones_del_libro(mundo) == []
    assert condonar_ok(mundo, "1A", SEP, "100.00")["importe"] == "100.00", "control: con el cuerpo bueno sí se condona"


def test_n01_condonar_mas_que_el_interes_pendiente_da_422_sin_cambios(mundo: Mundo) -> None:
    """Escenario: la `1A` debe 510,00 de interés de septiembre; se piden 510,01 y, tras condonar 200,00, 310,01"""
    armar_la_deuda(mundo)
    antes = del_libro(mundo)
    sep = obligacion_de(mundo, "1A", SEP)
    assert condonar(mundo, "1A", cuerpo_de_condonacion(sep, "510.01")).status_code == 422
    sin_cambios(mundo, antes, 0, "condonar_intereses", "510,01 de 510,00")
    condonar_ok(mundo, "1A", SEP, "200.00")
    despues, auditadas = del_libro(mundo), len(auditorias(mundo, "condonar_intereses"))
    assert condonar(mundo, "1A", cuerpo_de_condonacion(sep, "310.01")).status_code == 422
    sin_cambios(mundo, despues, auditadas, "condonar_intereses", "310,01 de 310,00")
    assert intereses_pendientes(mundo, "1A")[SEP] == 310


def test_n01_condonar_algo_que_no_es_interes_pendiente_da_422_sin_cambios(mundo: Mundo) -> None:
    """Escenario: noviembre de la `1A` sólo tiene capital; la `1B` pagó a término y no tiene interés alguno"""
    armar_la_deuda(mundo)
    antes = del_libro(mundo)
    for unidad, periodo in (("1A", NOV), ("1B", SEP), ("1B", OCT)):
        r = condonar(mundo, unidad, cuerpo_de_condonacion(obligacion_de(mundo, unidad, periodo), "1.00"))
        assert r.status_code == 422, f"{unidad} {periodo}: se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
        sin_cambios(mundo, antes, 0, "condonar_intereses", f"{unidad} {periodo}")


def test_n01_condonar_un_interes_ya_cobrado_da_422_sin_cambios(mundo: Mundo) -> None:
    """Escenario: la `1A` paga 10.510,00 el 17/11 y el interés de septiembre queda cobrado (lo cobrado de más sigue
    por el ajuste de interés, H-021)"""
    armar_la_deuda(mundo)
    pagar(mundo, "1A", "10510.00", date(2026, 11, 17))
    assert intereses_pendientes(mundo, "1A")[SEP] == 0, "control: septiembre ya está cobrado"
    antes = del_libro(mundo)
    r = condonar(mundo, "1A", cuerpo_de_condonacion(obligacion_de(mundo, "1A", SEP), "1.00"))
    assert r.status_code == 422, f"se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
    sin_cambios(mundo, antes, 0, "condonar_intereses", "interés ya cobrado")


# --- N02: perfiles y alcance -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("rol", SIN_PERMISO)
def test_n02_fuera_del_super_admin_y_la_principal_condonar_da_403_sin_cambios(mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} intenta condonar 100,00 de la `1A`"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "100.00")  # control: quien puede, puede
    antes = del_libro(mundo)
    mundo.como(rol)
    r = condonar(mundo, "1A", cuerpo_de_condonacion(obligacion_de(mundo, "1A", SEP), "100.00"))
    sin_permiso(r, f"condonar como {rol}", "condonar_intereses")
    sin_cambios(mundo, antes, 1, "condonar_intereses", rol)


@pytest.mark.parametrize("rol", SIN_PERMISO)
def test_n02_fuera_del_super_admin_y_la_principal_marcar_y_desmarcar_dan_403_sin_cambios(
        mundo: Mundo, rol: str) -> None:
    """Escenario: {rol} intenta marcar la `2A` y desmarcar la `1A` (marcada por el super admin)"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "1A")
    mundo.como(rol)
    sin_permiso(marcar(mundo, "2A"), f"marcar como {rol}", "marcar_gestion_judicial")
    sin_permiso(desmarcar(mundo, "1A"), f"desmarcar como {rol}", "desmarcar_gestion_judicial")
    assert [f[2] for f in marcas_del_historial(mundo)] == ["marcar"], "no quedó nada nuevo"
    assert (len(auditorias(mundo, "marcar_gestion_judicial")), len(auditorias(mundo, "desmarcar_gestion_judicial"))) == (
        1, 0)


def test_n02_lo_ajeno_no_existe_para_condonar_ni_para_marcar(mundo: Mundo) -> None:
    """Escenario: unidades de otro edificio o de otra administración, edificios ajenos, obligaciones que no son de la
    unidad y personas fuera del alcance; todo 404 con el mismo cuerpo, sin cambios"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "2A")
    antes = del_libro(mundo)
    propia = cuerpo_de_condonacion(obligacion_de(mundo, "1A", SEP), "100.00")
    no_encontrado(condonar(mundo, mundo.unidad_otro, propia), "condonar la 9A por el edificio de la 1A")
    no_encontrado(condonar(mundo, mundo.unidad_b, propia), "condonar una unidad de la administración B")
    no_encontrado(condonar(mundo, uuid4(), propia), "condonar una unidad inexistente")
    no_encontrado(condonar(mundo, "1A", propia, complejo=uuid4()), "condonar con un edificio inexistente")
    no_encontrado(condonar(mundo, "1A", cuerpo_de_condonacion(obligacion_de(mundo, "1B", SEP), "1.00")),
                  "una obligación de la 1B para la 1A")
    no_encontrado(condonar(mundo, "1A", cuerpo_de_condonacion(uuid4(), "1.00")), "una obligación inexistente")
    for dueño in (mundo.unidad_otro, mundo.unidad_b, uuid4()):
        no_encontrado(marcar(mundo, dueño), f"marcar {dueño}")
        no_encontrado(desmarcar(mundo, dueño), f"desmarcar {dueño}")
    mundo.como("admin_de_otro_edificio")
    no_encontrado(condonar(mundo, "1A", propia), "un administrador de otro edificio (el alcance va antes)")
    no_encontrado(marcar(mundo, "1A"), "marcar con un administrador de otro edificio")
    no_encontrado(desmarcar(mundo, "2A"), "desmarcar con un administrador de otro edificio")
    mundo.como("administracion_b")
    no_encontrado(condonar(mundo, "1A", propia), "condonar la 1A desde la administración B")
    no_encontrado(marcar(mundo, "1A"), "marcar la 1A desde la administración B")
    no_encontrado(desmarcar(mundo, "2A"), "desmarcar la 2A desde la administración B")
    no_encontrado(condonaciones_del_edificio(mundo), "leer las condonaciones desde la administración B")
    mundo.como("super_admin")
    sin_cambios(mundo, antes, 0, "condonar_intereses", "lo ajeno")
    assert [f[2] for f in marcas_del_historial(mundo)] == ["marcar"], "sólo la marca del control"


def test_n02_la_lectura_de_condonaciones_del_edificio_pide_su_permiso(mundo: Mundo) -> None:
    """Escenario: el auxiliar y la vecina no leen el listado del edificio; un administrador de otro edificio, 404"""
    armar_la_deuda(mundo)
    condonar_ok(mundo, "1A", SEP, "100.00")
    for rol in ("auxiliar", "ana"):
        mundo.como(rol)
        sin_permiso(condonaciones_del_edificio(mundo), f"leer las condonaciones como {rol}", "ver_condonaciones")
    mundo.como("admin_de_otro_edificio")
    no_encontrado(condonaciones_del_edificio(mundo), "un administrador de otro edificio")


# --- N03: la marca judicial no toca el libro ---------------------------------------------------------------------------


def test_n03_marcar_y_desmarcar_no_cambian_el_saldo_ni_escriben_en_el_libro(mundo: Mundo) -> None:
    """Escenario: marcar, desmarcar y marcar la `1A` deja movimiento, imputación, obligación y cuenta idénticos"""
    armar_la_deuda(mundo)
    antes, saldo = del_libro(mundo), saldo_de(mundo, "1A")
    marcar_ok(mundo, "1A")
    assert del_libro(mundo) == antes and saldo_de(mundo, "1A") == saldo, "marcar no escribe en el libro"
    desmarcar_ok(mundo, "1A")
    marcar_ok(mundo, "1A")
    assert del_libro(mundo) == antes and saldo_de(mundo, "1A") == saldo
    assert condonaciones_del_libro(mundo) == [], "marcar no es condonar"


def test_n03_la_marca_no_frena_el_interes_ni_cambia_la_deuda_del_certificado(mundo: Mundo) -> None:
    """Escenario: la `1A` marcada sigue debiendo 30.720,00 y su interés corrido sigue corriendo (440,00 al 18/11)"""
    armar_la_deuda(mundo)
    corrido = interes_corrido_del_libro(mundo, "1A", HOY)
    sin_marca = emitir_certificado(mundo, "1A", HOY)
    marcar_ok(mundo, "1A")
    marcada = emitir_certificado(mundo, "1A", HOY)
    assert marcada["en_gestion_judicial"] is True and sin_marca["en_gestion_judicial"] is False
    assert (marcada["saldo"], marcada["capital"], marcada["intereses"], marcada["interes_corrido"],
            marcada["libre_de_deuda"]) == ("30720.00", "30000.00", "720.00", f"{corrido:.2f}", False), marcada
    assert marcada["interes_corrido"] == "440.00" == sin_marca["interes_corrido"]
    assert marcada["saldo"] == sin_marca["saldo"]


# --- N04: marcar de más o desmarcar de más da 409; el cuerpo inválido, 422 --------------------------------------------


def test_n04_marcar_una_unidad_ya_marcada_da_409_sin_cambios(mundo: Mundo) -> None:
    """Escenario: la `1A` ya está marcada y se pide marcarla otra vez, con el mismo motivo y con otro"""
    armar_la_deuda(mundo)
    marcar_ok(mundo, "1A", "Primera marca")
    antes = del_libro(mundo)
    for motivo in ("Primera marca", "Otro motivo"):
        r = marcar(mundo, "1A", {"motivo": motivo})
        assert r.status_code == 409, f"se esperaba 409, llegó {r.status_code}: {r.text[:300]}"
    sin_cambios(mundo, antes, 0, "condonar_intereses", "marcar dos veces")
    assert [(f[2], f[3]) for f in marcas_del_historial(mundo)] == [("marcar", "Primera marca")]
    assert len(auditorias(mundo, "marcar_gestion_judicial")) == 1, "el 409 no se audita"


def test_n04_desmarcar_una_unidad_que_no_esta_marcada_da_409_sin_cambios(mundo: Mundo) -> None:
    """Escenario: la `1A` nunca se marcó; la `2A` se marcó, se desmarcó y se pide desmarcarla otra vez"""
    armar_la_deuda(mundo)
    assert desmarcar(mundo, "1A").status_code == 409, "nunca marcada"
    marcar_ok(mundo, "2A")
    desmarcar_ok(mundo, "2A")
    assert desmarcar(mundo, "2A").status_code == 409, "ya desmarcada"
    assert [(f[1], f[2]) for f in marcas_del_historial(mundo)] == [
        (mundo.unidades["2A"], "marcar"), (mundo.unidades["2A"], "desmarcar")], "sólo lo del control"
    assert (len(auditorias(mundo, "marcar_gestion_judicial")), len(auditorias(mundo, "desmarcar_gestion_judicial"))) == (
        1, 1)


def test_n04_un_cuerpo_invalido_da_422_antes_que_el_409_y_no_deja_rastro(mundo: Mundo) -> None:
    """Escenario: motivo ausente, vacío, en blanco, nulo, largo o numérico, o un campo de más, al marcar y al desmarcar"""
    armar_la_deuda(mundo)
    cuerpos: dict[str, Any] = {
        "sin motivo": {}, "motivo vacío": {"motivo": ""}, "motivo en blanco": {"motivo": "   "},
        "motivo nulo": {"motivo": None}, "motivo de 501": {"motivo": MOTIVO_LARGO}, "motivo numérico": {"motivo": 5},
        "campo de más": {"motivo": "Motivo", "unidad_id": str(mundo.unidades["2A"])},
    }
    for nombre, cuerpo in cuerpos.items():
        r = marcar(mundo, "1A", cuerpo)
        assert r.status_code == 422, f"marcar, {nombre}: se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
    assert marcas_del_historial(mundo) == [] and auditorias(mundo, "marcar_gestion_judicial") == []
    marcar_ok(mundo, "1A")
    for nombre, cuerpo in cuerpos.items():
        r = marcar(mundo, "1A", cuerpo)
        assert r.status_code == 422, f"marcar una marcada, {nombre}: 422 antes que el 409, llegó {r.status_code}"
        r = desmarcar(mundo, "1A", cuerpo)
        assert r.status_code == 422, f"desmarcar, {nombre}: se esperaba 422, llegó {r.status_code}: {r.text[:300]}"
        r = desmarcar(mundo, "2A", cuerpo)
        assert r.status_code == 422, f"desmarcar una no marcada, {nombre}: 422 antes que el 409, llegó {r.status_code}"
    assert [f[2] for f in marcas_del_historial(mundo)] == ["marcar"], "sólo la marca del control"
