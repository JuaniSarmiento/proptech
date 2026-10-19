"""Un espacio al borde no hace que "1A " sea otra unidad que "1A", ni que
" limpieza" sea otra categoría que "Limpieza" (R3A-6, decisión del 3a).

Spec: identificador único dentro del edificio; nombre de categoría único sin
distinguir mayúsculas (409). La base los guardaba tal cual, con el espacio,
así que dos valores que se ven iguales en el padrón y en la boleta convivían
como registros distintos. Decisión: normalizar (recortar), no rechazar —
misma función (`recortado_sin_control`, R3A-1) que ya se usa en toda la
familia de texto libre: identificador de unidad, nombre de grupo y de
categoría, nombre y localidad de edificio.
"""

from uuid import UUID

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

UNIDAD = {
    "tipo": "departamento",
    "piso": "1",
    "coeficiente": "0.100000",
    "superficie_m2": "60.00",
}


def test_identificador_con_espacio_al_final_no_es_otra_unidad(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    # "1A" ya existe en el edificio (lo siembra el fixture).
    respuesta = api.cliente.post(api.ruta("/unidades"), json={**UNIDAD, "identificador": "1A "})
    assert respuesta.status_code == 409, (respuesta.status_code, respuesta.text)
    assert respuesta.json() == {"detail": "conflicto", "campo": "identificador"}


def test_nombre_de_categoria_con_espacio_no_es_otra_categoria(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    nombres = [c["nombre"] for c in api.cliente.get(api.ruta("/categorias")).json()]
    existente = nombres[0]
    respuesta = api.cliente.post(
        api.ruta("/categorias"), json={"clave": "copia_rompedor", "nombre": " " + existente.lower()}
    )
    assert respuesta.status_code == 409, (respuesta.status_code, respuesta.text)
    assert respuesta.json() == {"detail": "conflicto", "campo": "nombre"}


def test_identificador_sin_espacios_al_borde_se_guarda_recortado(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    alta = api.cliente.post(api.ruta("/unidades"), json={**UNIDAD, "identificador": "  9Z  "})
    assert alta.status_code == 201, alta.text
    assert alta.json()["identificador"] == "9Z"


def test_nombre_y_localidad_de_edificio_sin_espacios_al_borde(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    alta = api.cliente.post(
        "/api/complejos", json={"nombre": "  Edificio Nuevo  ", "localidad": "  Mendoza  "}
    )
    assert alta.status_code == 201, alta.text
    edificio = api.cliente.get(f"/api/complejos/{alta.json()['id']}").json()
    assert edificio["nombre"] == "Edificio Nuevo"
    assert edificio["localidad"] == "Mendoza"


def test_nombre_de_grupo_sin_espacios_al_borde(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    alta = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": "parrilla",
            "nombre": "  Parrilla  ",
            "metodo": "coeficiente",
            "unidades": [{"unidad_id": str(api.unidad)}],
        },
    )
    assert alta.status_code == 201, alta.text
    grupo_id = UUID(alta.json()["id"])
    grupos = api.cliente.get(api.ruta("/grupos")).json()
    parrilla = next(g for g in grupos if g["id"] == str(grupo_id))
    assert parrilla["nombre"] == "Parrilla"
