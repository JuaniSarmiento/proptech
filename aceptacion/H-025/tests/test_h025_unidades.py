"""H-025 · la ruta de las unidades para informar (N02 del lado de la API). Contrato en
`aceptacion/H-025/CONTRATO.md`."""

from __future__ import annotations

import pytest

from ._h025 import Mundo, ruta


def _unidades(m: Mundo) -> list[str]:
    r = m.cliente.get(ruta(m, "/unidades"))
    assert r.status_code == 200, f"unidades: se esperaba 200, llegó {r.status_code}: {r.text[:300]}"
    lista = r.json()
    for u in lista:
        assert set(u) == {"unidad_id", "identificador"}, u
        assert u["unidad_id"] == str(m.unidades[u["identificador"]])
    return [u["identificador"] for u in lista]


def test_n02_la_vecina_ve_sus_unidades(mundo: Mundo) -> None:
    mundo.como("ana")
    assert _unidades(mundo) == ["1A", "2B"]
    mundo.como("beto")
    assert _unidades(mundo) == ["1B"]


@pytest.mark.parametrize("rol", ["admin_principal", "admin_del_edificio", "super_admin"])
def test_n02_el_personal_ve_todas(mundo: Mundo, rol: str) -> None:
    mundo.como(rol)
    assert _unidades(mundo) == ["1A", "1B", "2A", "2B"]


def test_n02_sin_permiso_o_fuera_del_alcance(mundo: Mundo) -> None:
    mundo.como("consejo")
    assert mundo.cliente.get(ruta(mundo, "/unidades")).status_code == 403
    mundo.como("admin_de_otro_edificio")
    r = mundo.cliente.get(ruta(mundo, "/unidades"))
    assert r.status_code == 404 and r.json() == {"detail": "no encontrado"}, r.text[:200]
