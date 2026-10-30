"""Rompedor pulido-2: la clave de un grupo también se puede mandar en PATCH."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize("clave", ["Mayuscula", "1x", "con espacio", "a" * 41, "ñandú", "abc\n"])
def test_patch_de_grupo_con_clave_invalida_da_422_y_no_cambia(
    api_edificio: ApiEdificio, clave: str
) -> None:
    api = api_edificio
    api.como("super_admin")
    alta = api.cliente.post(
        api.ruta("/grupos"), json={"clave": "torre_a", "nombre": "Torre A", "metodo": "coeficiente"}
    )
    assert alta.status_code == 201, alta.text
    gid = alta.json()["id"]
    r = api.cliente.patch(f"/api/grupos/{gid}", json={"clave": clave})
    assert r.status_code == 422, r.text
    assert clave not in r.text
    assert api.filas("SELECT clave FROM grupo_de_reparto WHERE id=%s", (gid,))[0][0] == "torre_a"
