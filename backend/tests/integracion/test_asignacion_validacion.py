"""Vocabulario asignable y campos extra rechazados en el borde (D7, R5 del 2a)."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize(
    ("cuerpo", "campo"),
    [
        ({"rol": rol}, "rol")
        for rol in ("super_admin", "vecino", "titular", "colaborador", "inventado")
    ]
    + [
        ({"rol": "administrador", campo: valor}, campo)
        for campo, valor in (
            ("nivel", "editar"),
            ("vinculo", "propietario"),
            ("unidad_id", "10000000-0000-0000-0000-000000000001"),
        )
    ]
    + [({"rol": "consejo", "nivel": "ver"}, "nivel")],
)
def test_cuerpo_fuera_de_lo_asignable_da_422_y_no_escribe(
    api_edificio: ApiEdificio, cuerpo: dict[str, str], campo: str
) -> None:
    api = api_edificio
    api.como("titular")
    consulta = "SELECT (SELECT count(*) FROM asignacion_rol), (SELECT count(*) FROM auditoria)"
    antes = api.filas(consulta)
    respuesta = api.cliente.post(
        api.ruta("/asignaciones"), json={"persona_id": str(api.personas["vecino"]), **cuerpo}
    )
    assert respuesta.status_code == 422, respuesta.text
    assert ["body", campo] in [error["loc"] for error in respuesta.json()["detail"]]
    assert api.filas(consulta) == antes


@pytest.mark.parametrize("rol", ["administrador", "contador", "auxiliar", "consejo"])
def test_roles_asignables_dan_201(api_edificio: ApiEdificio, rol: str) -> None:
    api = api_edificio
    api.como("titular")
    respuesta = api.cliente.post(
        api.ruta("/asignaciones"), json={"persona_id": str(api.personas["vecino"]), "rol": rol}
    )
    assert respuesta.status_code == 201, respuesta.text
