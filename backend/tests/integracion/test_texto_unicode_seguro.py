"""Frente 2: la familia de `compartido/texto.py` (R3A-1, R3A-6) más allá de
los casos que escribió su autor."""

import json

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

UNIDAD = {"tipo": "departamento", "piso": "1", "coeficiente": "0.100000", "superficie_m2": "60.00"}


@pytest.mark.parametrize(
    "invisible",
    ["​", "⁠", "﻿", "­"],
    ids=["zero_width_space", "word_joiner", "bom", "soft_hyphen"],
)
def test_identificador_con_caracter_invisible_no_es_otra_unidad(
    api_edificio: ApiEdificio, invisible: str
) -> None:
    """R3A-6 decidió que "1A " y "1A" son la misma unidad porque se ven
    iguales en el padrón y en la boleta. `str.strip()` no saca los
    caracteres de formato (categoría Cf) y `sin_caracteres_de_control` sólo
    mira Cc: "1A" + U+200B se ve idéntico a "1A" y entra como unidad nueva."""
    api = api_edificio
    api.como("super_admin")
    respuesta = api.cliente.post(
        api.ruta("/unidades"), json={**UNIDAD, "identificador": "1A" + invisible}
    )
    assert respuesta.status_code in (409, 422), (respuesta.status_code, respuesta.text)


@pytest.mark.parametrize(
    ("ruta", "cuerpo"),
    [
        ("/unidades", {**UNIDAD, "identificador": "X\ud800"}),
        ("/unidades", {**UNIDAD, "identificador": "7Q", "piso": "\udfff"}),
        ("/categorias", {"clave": "sustituto", "nombre": "N\ud800"}),
        ("/grupos", {"clave": "sustituto", "nombre": "N\ud800", "metodo": "coeficiente"}),
    ],
    ids=["identificador", "piso", "categoria", "grupo"],
)
def test_surrogate_suelto_da_422_y_no_500(
    api_edificio: ApiEdificio, ruta: str, cuerpo: dict[str, str]
) -> None:
    """Mismo frente que R3A-1 (D6: ningún 500 con entrada del cliente), otra
    categoría Unicode: un `\\ud800` suelto es JSON válido, Python lo deja
    pasar como `str` (categoría Cs, no Cc) y no se puede codificar a UTF-8."""
    api = api_edificio
    api.como("super_admin")
    crudo = json.dumps(cuerpo)  # ensure_ascii: el surrogate viaja como \\ud800
    respuesta = api.cliente.post(
        api.ruta(ruta), content=crudo, headers={"Content-Type": "application/json"}
    )
    assert respuesta.status_code == 422, (respuesta.status_code, respuesta.text)
    assert all("input" not in e and "ctx" not in e for e in respuesta.json()["detail"])
    assert all(
        "\\ud800" not in str(e) and "\\udfff" not in str(e) for e in respuesta.json()["detail"]
    )


@pytest.mark.parametrize("caracter", ["\ud800", "\u200b", "\u202e", "\u034f", "\u3164"])
@pytest.mark.parametrize(
    "campo", ["nombre", "localidad", "piso", "identificador", "grupo", "categoria"]
)
def test_familia_de_textos_rechaza_unicode_inseguro_sin_eco(
    api_edificio: ApiEdificio, caracter: str, campo: str
) -> None:
    api = api_edificio
    valor = "MARCADOR" + caracter
    if campo in ("nombre", "localidad"):
        ruta = "/api/complejos"
        cuerpo = {"nombre": "Edificio", "localidad": "Mendoza", campo: valor}
        metodo = "POST"
    elif campo in ("piso", "identificador"):
        ruta = f"/api/unidades/{api.unidad}"
        cuerpo = {campo: valor}
        metodo = "PATCH"
    else:
        plural = "grupos" if campo == "grupo" else "categorias"
        datos = {"clave": "seguro", "nombre": "Seguro"}
        if campo == "grupo":
            datos["metodo"] = "coeficiente"
        alta = api.cliente.post(api.ruta("/" + plural), json=datos)
        assert alta.status_code == 201, alta.text
        ruta = f"/api/{plural}/{alta.json()['id']}"
        cuerpo = {"nombre": valor}
        metodo = "PATCH"
    respuesta = api.cliente.request(
        metodo, ruta, content=json.dumps(cuerpo), headers={"Content-Type": "application/json"}
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "MARCADOR" not in respuesta.text
    assert all("input" not in e and "ctx" not in e for e in respuesta.json()["detail"])
