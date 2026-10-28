"""Ningún texto libre del cliente admite un carácter de control (R3A-1,
cambio 3a, vuelta 1 de correcciones).

PostgreSQL no admite U+0000 en `text`; pydantic `str` lo aceptaba sin que
ninguna capa lo frenara, así que el error del driver salía como 500 (D6:
ningún 500 alcanzable con entrada del cliente; el contrato es 422 nombrando
el campo). `proptech_core.compartido.texto.sin_caracteres_de_control` /
`recortado_sin_control` cierran la familia completa: todo campo de texto
libre de toda ruta del 3a, tanto en el alta como en la edición.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

NUL = "A\u0000B"
UNIDAD = {
    "identificador": "9Z",
    "tipo": "departamento",
    "piso": "9",
    "coeficiente": "0.100000",
    "superficie_m2": "60.00",
}


_UBICACION_VALIDA = {
    "provincia_id": "50",
    "departamento_id": "50007",
    "localidad_id": "50007010",
    "pisos": 4,
    "subsuelos": 1,
}


def _casos(api: ApiEdificio) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        ("post", "/api/complejos", {"nombre": NUL, **_UBICACION_VALIDA}),
        # D2 (tarea 2.6): `localidad` dejó de ser una entrada; el carácter
        # de control se prueba ahora sobre `calle_y_numero`, el otro texto
        # libre opcional del alta.
        (
            "post",
            "/api/complejos",
            {"nombre": "Nuevo", **_UBICACION_VALIDA, "calle_y_numero": NUL},
        ),
        ("post", api.ruta("/unidades"), {**UNIDAD, "identificador": NUL}),
        ("post", api.ruta("/unidades"), {**UNIDAD, "piso": NUL}),
        ("patch", f"/api/unidades/{api.unidad}", {"piso": NUL}),
        ("patch", f"/api/unidades/{api.unidad}", {"identificador": NUL}),
        (
            "post",
            api.ruta("/grupos"),
            {"clave": "pileta", "nombre": NUL, "metodo": "coeficiente", "unidades": []},
        ),
        ("post", api.ruta("/categorias"), {"clave": "nocturna", "nombre": NUL}),
    ]


@pytest.mark.parametrize("indice", range(8))
def test_texto_con_caracter_de_control_da_422_y_no_500(
    api_edificio: ApiEdificio, indice: int
) -> None:
    api = api_edificio
    api.como("super_admin")
    cliente = TestClient(api.app, raise_server_exceptions=False)
    metodo, ruta, cuerpo = _casos(api)[indice]
    respuesta = getattr(cliente, metodo)(ruta, json=cuerpo)
    assert respuesta.status_code == 422, (metodo, ruta, respuesta.status_code, respuesta.text)


@pytest.mark.parametrize("contexto", ["existente", "inexistente", "sin_permiso"])
def test_patch_de_grupo_con_caracter_de_control_en_el_nombre_da_422(
    api_edificio: ApiEdificio,
    contexto: str,
) -> None:
    api = api_edificio
    api.como("super_admin")
    alta = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": "lavadero",
            "nombre": "Lavadero",
            "metodo": "coeficiente",
            "unidades": [{"unidad_id": str(api.unidad)}],
        },
    )
    assert alta.status_code == 201, alta.text
    recurso_id = str(uuid4()) if contexto == "inexistente" else alta.json()["id"]
    if contexto == "sin_permiso":
        api.como("consejo")
    cliente = TestClient(api.app, raise_server_exceptions=False)
    respuesta = cliente.patch(f"/api/grupos/{recurso_id}", json={"nombre": NUL})
    assert respuesta.status_code == 422, (respuesta.status_code, respuesta.text)


@pytest.mark.parametrize("contexto", ["existente", "inexistente", "sin_permiso"])
def test_patch_de_categoria_con_caracter_de_control_en_el_nombre_da_422(
    api_edificio: ApiEdificio,
    contexto: str,
) -> None:
    api = api_edificio
    api.como("super_admin")
    alta = api.cliente.post(api.ruta("/categorias"), json={"clave": "diurna", "nombre": "Diurna"})
    assert alta.status_code == 201, alta.text
    recurso_id = str(uuid4()) if contexto == "inexistente" else alta.json()["id"]
    if contexto == "sin_permiso":
        api.como("consejo")
    cliente = TestClient(api.app, raise_server_exceptions=False)
    respuesta = cliente.patch(f"/api/categorias/{recurso_id}", json={"nombre": NUL})
    assert respuesta.status_code == 422, (respuesta.status_code, respuesta.text)
