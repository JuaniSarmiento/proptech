"""H-035 · los propietarios de la unidad (C01, C02) y los nombres del historial (C03).

Hoy `.../unidades/{u}/propietarios` no existe (404 contra el 200 esperado: aserción) y el historial no trae
`vendedores_detalle`. Los cambios se arman con la ruta real de H-030 (que ya existe).
"""

from __future__ import annotations

from typing import Any

from ._h035 import (
    CLAVES_DEL_CAMBIO,
    Mundo,
    auditorias,
    con_nombres_ok,
    del_libro,
    detalle_de,
    listar,
    pares,
    propietarios,
    propietarios_ok,
    registrar_con_nombres_ok,
    registrar_ok,
)

PERFILES = ("super_admin", "admin_principal", "admin_del_edificio")


def _de(m: Mundo, *claves: str) -> list[tuple[str, str]]:
    nombres = {"ana": "Ana Prueba", "carla": "Carla Prueba", "dora": "Dora Prueba", "edu": "Edu Prueba",
               "beto": "Beto Prueba"}
    return [(str(m.personas[c]), nombres[c]) for c in claves]


def test_c01_los_tres_perfiles_leen_los_propietarios_de_la_unidad(mundo: Mundo) -> None:
    """Escenario: `registrar_cambio_de_titular` lo tienen el super admin y los dos administradores"""
    for rol in PERFILES:
        mundo.como(rol)
        assert pares(propietarios_ok(mundo, "2A")) == _de(mundo, "dora", "edu"), rol


def test_c01_una_unidad_con_un_solo_propietario(mundo: Mundo) -> None:
    assert pares(propietarios_ok(mundo, "1A")) == _de(mundo, "ana")
    assert pares(propietarios_ok(mundo, "1B")) == _de(mundo, "carla")


def test_c01_leer_los_propietarios_no_escribe_ni_audita(mundo: Mundo) -> None:
    assert propietarios_ok(mundo, "2A"), "precondición: la unidad tiene propietarios"
    antes = (del_libro(mundo), auditorias(mundo), auditorias(mundo, "ver_propietarios"))
    propietarios_ok(mundo, "2A")
    assert (del_libro(mundo), auditorias(mundo), auditorias(mundo, "ver_propietarios")) == antes


def test_c02_no_trae_inquilinos(mundo: Mundo) -> None:
    assert pares(propietarios_ok(mundo, "1B")) == _de(mundo, "carla"), "Beto es inquilino de 1B"


def test_c02_no_trae_propietarios_de_otras_unidades(mundo: Mundo) -> None:
    """Ana es propietaria de 1A y 2B: en 2A no aparece, y Dora y Edu no aparecen en 1A ni en 2B."""
    en_2a = {p for p, _ in pares(propietarios_ok(mundo, "2A"))}
    assert str(mundo.personas["ana"]) not in en_2a and en_2a
    for unidad in ("1A", "2B"):
        assert pares(propietarios_ok(mundo, unidad)) == _de(mundo, "ana"), unidad


def test_c02_despues_de_un_cambio_trae_a_los_compradores_y_ya_no_a_los_vendedores(mundo: Mundo) -> None:
    """Los compradores se piden en orden inverso al alfabético: la lista sale por nombre."""
    cambio = registrar_ok(mundo, "2A", [mundo.personas["dora"], mundo.personas["edu"]],
                          [{"nombre": "Zeta Compradora", "email": None}, {"nombre": "Alfa Compradora",
                                                                         "email": None}])
    ids: dict[str, str] = {c["nombre"]: str(c["persona_id"]) for c in cambio["compradores"]}
    esperados = [(ids["Alfa Compradora"], "Alfa Compradora"), (ids["Zeta Compradora"], "Zeta Compradora")]
    assert pares(propietarios_ok(mundo, "2A")) == esperados


def test_c03_el_post_suma_el_nombre_de_cada_vendedor_y_comprador(mundo: Mundo) -> None:
    """Contrato: con `?con_nombres=true`, `vendedores_detalle` va junto a `vendedores` (ids, igual que antes)."""
    cambio = registrar_con_nombres_ok(mundo, "2A", [mundo.personas["dora"], mundo.personas["edu"]],
                                      [{"nombre": "Nora Compradora", "email": None}])
    assert cambio["vendedores"] == [str(mundo.personas["dora"]), str(mundo.personas["edu"])], cambio
    assert pares(detalle_de(cambio)) == _de(mundo, "dora", "edu"), cambio
    assert [c["nombre"] for c in cambio["compradores"]] == ["Nora Compradora"]


def test_c03_el_get_trae_los_nombres_aunque_ya_no_sean_propietarios(mundo: Mundo) -> None:
    registrar_ok(mundo, "2A", [mundo.personas["dora"]], [{"nombre": "Nora Compradora", "email": None}])
    registrar_ok(mundo, "2A", [mundo.personas["edu"]], [{"nombre": "Omar Comprador", "email": None}])
    historial = con_nombres_ok(mundo, "2A")
    assert len(historial) == 2, historial
    nuevo, viejo = historial
    assert pares(detalle_de(nuevo)) == _de(mundo, "edu"), nuevo
    assert pares(detalle_de(viejo)) == _de(mundo, "dora"), viejo
    assert [c["nombre"] for c in nuevo["compradores"]] == ["Omar Comprador"]
    assert [c["nombre"] for c in viejo["compradores"]] == ["Nora Compradora"]
    ahora = {p for p, _ in pares(propietarios_ok(mundo, "2A"))}
    assert str(mundo.personas["dora"]) not in ahora and str(mundo.personas["edu"]) not in ahora, ahora


def test_c03_sin_el_parametro_las_respuestas_no_cambian(mundo: Mundo) -> None:
    """Las aceptaciones de H-030 a H-033 fijan las claves exactas del 201 y del historial: no se tocan."""
    cambio: dict[str, Any] = registrar_ok(mundo, "2A", [mundo.personas["dora"]])
    assert set(cambio) == CLAVES_DEL_CAMBIO, sorted(cambio)
    assert cambio["vendedores"] == [str(mundo.personas["dora"])]
    r = listar(mundo, "2A")
    assert r.status_code == 200 and all("vendedores_detalle" not in c for c in r.json()), r.text[:300]
    assert propietarios(mundo, "2A").status_code == 200, "precondición: la ruta nueva existe"
