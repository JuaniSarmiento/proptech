"""H-035 · lo que no tiene que pasar (N01, N02).

Cada test pide primero el 200 del administrador: una ruta que no existe (404) o que siempre contesta lo mismo no
pasa por casualidad.
"""

from __future__ import annotations

import json
from uuid import uuid4

from ._h035 import (
    CLAVES_DEL_PROPIETARIO,
    EMAIL_DE_ANA,
    EMAIL_DE_DORA,
    Mundo,
    con_nombres_ok,
    detalle_de,
    no_encontrado,
    propietarios,
    propietarios_ok,
    registrar_con_nombres_ok,
    ruta,
    ruta_propietarios,
    sin_permiso,
)

SIN_PERMISO = ("contador", "contador_del_edificio", "auxiliar", "consejo", "ana", "carla", "beto")
FUERA = ("admin_de_otro_edificio", "consejo_de_otro_edificio", "administracion_b")


def test_n01_sin_el_permiso_da_403_y_no_se_filtra_nada(mundo: Mundo) -> None:
    assert propietarios_ok(mundo, "2A"), "precondición: el administrador sí los lee"
    for rol in SIN_PERMISO:
        mundo.como(rol)
        r = propietarios(mundo, "2A")
        sin_permiso(r)
        assert "Dora" not in r.text and "propietarios" not in r.json(), (rol, r.text)


def test_n01_fuera_de_alcance_da_404_antes_que_403(mundo: Mundo) -> None:
    """Escenario: unidad de otro edificio, edificio de otra administración, unidad inexistente; el 404 gana al 403"""
    assert propietarios_ok(mundo, "2A"), "precondición: el administrador sí los lee"
    no_encontrado(mundo.cliente.get(ruta_propietarios(mundo, complejo=mundo.otro, unidad_id=mundo.unidades["2A"])))
    no_encontrado(mundo.cliente.get(ruta_propietarios(mundo, complejo=mundo.edificio_b,
                                                      unidad_id=mundo.unidades["2A"])))
    no_encontrado(mundo.cliente.get(ruta_propietarios(mundo, unidad_id=uuid4())))
    no_encontrado(mundo.cliente.get(ruta_propietarios(mundo, complejo=uuid4(), unidad_id=mundo.unidades["2A"])))
    for rol in FUERA:
        mundo.como(rol)
        no_encontrado(propietarios(mundo, "2A"))


def test_n02_cada_propietario_trae_solo_id_y_nombre_sin_email(mundo: Mundo) -> None:
    for unidad in ("1A", "2A"):
        lista = propietarios_ok(mundo, unidad)
        assert lista and all(set(p) == CLAVES_DEL_PROPIETARIO for p in lista), lista
    texto = json.dumps([propietarios_ok(mundo, "1A"), propietarios_ok(mundo, "2A")])
    assert EMAIL_DE_ANA not in texto and EMAIL_DE_DORA not in texto and "@" not in texto, texto


def test_n02_el_detalle_de_vendedores_trae_solo_id_y_nombre_sin_email(mundo: Mundo) -> None:
    cambio = registrar_con_nombres_ok(mundo, "2A", [mundo.personas["dora"]],
                                      [{"nombre": "Nora Compradora", "email": None}])
    historial = con_nombres_ok(mundo, "2A")
    for c in (cambio, *historial):
        detalle = detalle_de(c)
        assert detalle and all(set(v) == CLAVES_DEL_PROPIETARIO for v in detalle), c
        assert EMAIL_DE_DORA not in json.dumps(detalle), detalle


def test_n01_el_historial_con_nombres_pide_el_mismo_permiso(mundo: Mundo) -> None:
    registrar_con_nombres_ok(mundo, "2A", [mundo.personas["dora"]], [{"nombre": "Nora Compradora", "email": None}])
    assert detalle_de(con_nombres_ok(mundo, "2A")[0]), "precondición: el administrador ve los nombres"
    for rol in ("contador", "auxiliar", "consejo", "carla"):
        mundo.como(rol)
        r = mundo.cliente.get(f"{ruta(mundo, '2A')}?con_nombres=true")
        sin_permiso(r)
        assert "Dora" not in r.text, (rol, r.text)
