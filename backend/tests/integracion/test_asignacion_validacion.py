"""`rol`/`nivel` de `POST /api/complejos/{id}/asignaciones` validados en el
cuerpo (R3A-4, deuda del 2a alcanzable desde el 3a).

`CuerpoAsignacion.rol`/`nivel` eran `str` libres: llegaban crudos al INSERT
de `asignacion_rol` y un valor que no matcheara alguno de los CHECK de la
migración 0003 (`ck_asignacion_rol_rol_valido`, `ck_asignacion_rol_nivel_
valido`, `ck_asignacion_rol_forma_por_rol`) terminaba en 500 (D6: ningún 500
alcanzable con entrada del cliente). Este endpoint siempre fija
`complejo_id` (del path) y nunca manda `unidad_id`, así que "titular" y
"vecino" nunca podrían satisfacer el CHECK de todos modos: el cuerpo sólo
acepta "colaborador" (con `nivel`) y "consejo" (sin `nivel`).
"""

import pytest
from fastapi.testclient import TestClient

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"rol": "vecino"},
        {"rol": "titular"},
        {"rol": "inventado"},
        {"rol": "colaborador", "nivel": "superusuario"},
        {"rol": "colaborador"},
        {"rol": "consejo", "nivel": "ver"},
    ],
    ids=[
        "vecino_sin_unidad_posible",
        "titular_sin_complejo_null_posible",
        "rol_inventado",
        "nivel_inventado",
        "colaborador_sin_nivel",
        "consejo_con_nivel",
    ],
)
def test_rol_o_nivel_invalido_en_asignacion_da_422_y_no_500(
    api_edificio: ApiEdificio, cuerpo: dict[str, str]
) -> None:
    api = api_edificio
    api.como("titular")
    cliente = TestClient(api.app, raise_server_exceptions=False)
    respuesta = cliente.post(
        api.ruta("/asignaciones"), json={"persona_id": str(api.personas["ver"]), **cuerpo}
    )
    assert respuesta.status_code == 422, (respuesta.status_code, respuesta.text)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"rol": "colaborador", "nivel": "editar"},
        {"rol": "consejo"},
    ],
    ids=["colaborador_con_nivel", "consejo_sin_nivel"],
)
def test_rol_y_nivel_validos_dan_201(api_edificio: ApiEdificio, cuerpo: dict[str, str]) -> None:
    """Control del test anterior (L-019): si la validación rechazara de
    más, estos dos (las únicas combinaciones que este endpoint soporta)
    también fallarían."""
    api = api_edificio
    api.como("titular")
    respuesta = api.cliente.post(
        api.ruta("/asignaciones"), json={"persona_id": str(api.personas["ver"]), **cuerpo}
    )
    assert respuesta.status_code == 201, (respuesta.status_code, respuesta.text)
