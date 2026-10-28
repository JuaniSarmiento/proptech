"""BE-002 (revisión del PR #2): la clave de una categoría se deriva del
nombre de punta a punta (HTTP + base), sin que el cliente la mande — el
mismo camino que `test_grupo_activo._grupo_parcial` ya ejercita para grupos.
Hasta ahora sólo `derivar_clave` estaba probada como función pura."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def _alta(api: ApiEdificio, nombre: str) -> dict[str, object]:
    r = api.cliente.post(api.ruta("/categorias"), json={"nombre": nombre})
    assert r.status_code == 201, r.text
    categoria_id = r.json()["id"]
    todas = api.cliente.get(api.ruta("/categorias")).json()
    return next(c for c in todas if c["id"] == categoria_id)


def test_crear_categoria_sin_clave_la_deriva_del_nombre(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("super_admin")
    categoria = _alta(api, "Seguridad Nocturna")
    assert categoria["clave"] == "seguridad_nocturna"
    filas = api.filas("SELECT clave FROM categoria_de_gasto WHERE id=%s", (str(categoria["id"]),))
    assert filas == [("seguridad_nocturna",)]


def test_dos_categorias_con_el_mismo_nombre_desempatan_la_clave(
    api_edificio: ApiEdificio,
) -> None:
    api = api_edificio
    api.como("super_admin")
    primera = _alta(api, "Jardinería")
    segunda = _alta(api, "jardineria")
    assert (primera["clave"], segunda["clave"]) == ("jardineria", "jardineria_2")


def test_nombre_sin_letras_y_sin_clave_da_422_en_nombre(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("super_admin")
    r = api.cliente.post(api.ruta("/categorias"), json={"nombre": "123"})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "nombre"]
