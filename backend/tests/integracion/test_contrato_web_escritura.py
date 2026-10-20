"""Guarda del contrato D4, lado escritura (R3C-1, vuelta de correcciones del
rompedor 3b): la web manda sus altas con `Content-Type: application/json`
(ver `web/src/lib/api/cliente.ts`, `pedirApi`). Antes del fix, un `body`
string sin ese header hacía que `fetch` pusiera `text/plain;charset=UTF-8`
(spec Fetch) y FastAPI, que sólo parsea JSON con `application/json` o
`+json`, daba 422 en TODA escritura (`detail: model_attributes_type`).

Con identidad inyectada (`api_edificio`), igual que `test_contrato_web.py`
hace para lectura: manda el Content-Type real que declara `pedirApi` y
también el roto (`text/plain`) a propósito, para que el contrato documente
las dos puntas.
"""

import json

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def test_alta_con_el_content_type_que_declara_pedirapi_funciona(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("super_admin")
    respuesta = api.cliente.post(
        api.ruta("/categorias"),
        content=json.dumps({"clave": "contrato_web", "nombre": "Contrato web"}),
        headers={"content-type": "application/json"},
    )
    assert respuesta.status_code == 201, respuesta.text


def test_alta_con_el_content_type_roto_que_mandaba_la_web_antes_del_fix_sigue_dando_422(
    api_edificio: ApiEdificio,
) -> None:
    """Guarda que la API real NO cambió: sigue exigiendo `application/json`.
    El fix de R3C-1 fue en la web (ahora declara el header), no acá — si
    este test empezara a dar 201, significa que esta guarda del contrato
    dejó de servir (la API relajó su parseo sin que nadie lo decidiera)."""
    api = api_edificio
    api.como("super_admin")
    respuesta = api.cliente.post(
        api.ruta("/categorias"),
        content=json.dumps({"clave": "contrato_web_roto", "nombre": "Contrato web roto"}),
        headers={"content-type": "text/plain;charset=UTF-8"},
    )
    assert respuesta.status_code == 422, respuesta.text
