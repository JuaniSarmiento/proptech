"""Vocabulario asignable y campos extra rechazados en el borde (D7, R5 del 2a)."""

import pytest
from fastapi.testclient import TestClient

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
    api.como("super_admin")
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
    api.como("super_admin")
    respuesta = api.cliente.post(
        api.ruta("/asignaciones"), json={"persona_id": str(api.personas["vecino"]), "rol": rol}
    )
    assert respuesta.status_code == 201, respuesta.text


def _cliente_sin_relanzar(api: ApiEdificio) -> TestClient:
    # Mismo app (mismos overrides de identidad), pero un 500 llega como
    # respuesta en vez de relanzarse: así se ve lo que vería el cliente.
    return TestClient(api.app, raise_server_exceptions=False)


@pytest.mark.parametrize("rol", ["administrador", "auxiliar", "contador"])
def test_asignar_un_segundo_perfil_de_personal_en_el_mismo_edificio_da_409_no_500(
    api_edificio: ApiEdificio, rol: str
) -> None:
    """Corrección RR-1 (rompedor, MEDIA): `editar` ya es administrador en
    `api.edificio`. El índice `uq_asignacion_rol_persona_alcance` (0017,
    RA-5) rechaza otra fila de personal en ese alcance; antes de la
    corrección el endpoint no traducía la violación y daba 500 crudo."""
    api = api_edificio
    api.como("super_admin")
    destino = api.personas["editar"]
    antes = api.filas("SELECT count(*) FROM asignacion_rol")
    auditoria = api.filas("SELECT count(*) FROM auditoria")
    # Sin `with`: no se vuelve a correr el lifespan (el motor ya está en
    # `app.state`), así no queda una segunda pila de conexiones abierta.
    respuesta = _cliente_sin_relanzar(api).post(
        api.ruta("/asignaciones"), json={"persona_id": str(destino), "rol": rol}
    )
    assert api.filas("SELECT count(*) FROM asignacion_rol") == antes
    assert api.filas("SELECT count(*) FROM auditoria") == auditoria
    assert respuesta.status_code == 409, (respuesta.status_code, respuesta.text)
    assert respuesta.json() == {"detail": "conflicto", "campo": "rol"}
