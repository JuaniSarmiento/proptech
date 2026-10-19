"""Revisión final (19/10/2026), arreglo 2: el eco de la clave en el 422 de
un campo no declarado (`extra_forbidden`).

R11/D7 exige que el 422 NOMBRE el campo (`loc`) — por eso el barrido de
`test_altas_sin_id_del_cliente.py` espera que `id` aparezca en `loc`. Pero
`loc` para `extra_forbidden` es la clave TAL CUAL la mandó el cliente
(`manejador_422`, `cuerpos.py`): con una clave de 10 KB o con HTML/JS, esa
misma regla hace que el 422 la repita completa, en el único lugar del
contrato pensado para nombrar campos, no para alojar lo que mande el
cliente (rompedor, vuelta 2, "eco de la clave").

Decisión: si la clave matchea `^[A-Za-z_][A-Za-z0-9_]{0,63}$` (un nombre de
campo razonable, R11 incluido: `id` matchea) se sigue nombrando tal cual;
si no, `loc` dice `"campo_no_permitido"`, sin la clave."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def _cuerpo(clave_extra: str) -> dict[str, object]:
    return {"clave": "control_422", "nombre": "Control", clave_extra: "lo que sea"}


def test_clave_no_permitida_razonable_se_sigue_nombrando(api_edificio: ApiEdificio) -> None:
    """Control del arreglo (L-019): si TODA clave se blanqueara, R11 (que
    pide nombrar `id`) se rompería con este mismo cambio."""
    api = api_edificio
    api.como("titular")
    respuesta = api.cliente.post(api.ruta("/categorias"), json=_cuerpo("id"))
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["detail"][0]["loc"][-1] == "id"


def test_clave_no_permitida_de_10kb_no_se_hace_eco(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    clave_gigante = "x" * 10_240
    respuesta = api.cliente.post(api.ruta("/categorias"), json=_cuerpo(clave_gigante))
    assert respuesta.status_code == 422, respuesta.text
    assert clave_gigante not in respuesta.text
    assert respuesta.json()["detail"][0]["loc"][-1] == "campo_no_permitido"


def test_clave_no_permitida_con_html_no_se_hace_eco(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    clave_con_html = "<script>alert(1)</script>"
    respuesta = api.cliente.post(api.ruta("/categorias"), json=_cuerpo(clave_con_html))
    assert respuesta.status_code == 422, respuesta.text
    assert clave_con_html not in respuesta.text
    assert "<script>" not in respuesta.text
    assert respuesta.json()["detail"][0]["loc"][-1] == "campo_no_permitido"
