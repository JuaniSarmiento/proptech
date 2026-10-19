"""Editar el método de un grupo propios conserva su coherencia (R3B-12)."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize("metodo", ["superficie", "partes_iguales"])
def test_grupo_propios_no_cambia_a_metodo_sin_coeficiente_por_patch(
    api_edificio: ApiEdificio, metodo: str
) -> None:
    """`grupos-de-reparto` > Dos modos: "Un grupo por superficie o en partes
    iguales MUST ser `renormalizado`". Ningún test de 5.3/6.2 hace PATCH del
    método de un grupo `propios`: el único guardián en la aplicación
    (`editar_grupo`, `if grupo["modo_de_coeficientes"] == "propios" and
    entrada.metodo != "coeficiente"`) se puede borrar y la suite sigue verde
    (mutante M2 del informe), y entonces el CHECK de 0007 revienta como 500.
    Este test pasa HOY: es el que mata ese mutante."""
    api = api_edificio
    api.como("titular")
    alta = api.cliente.post(
        api.ruta("/grupos"),
        json={
            "clave": f"propio_{metodo}",
            "nombre": "Propio",
            "metodo": "coeficiente",
            "modo_de_coeficientes": "propios",
            "unidades": [{"unidad_id": str(api.unidad), "coeficiente": "1"}],
        },
    )
    assert alta.status_code == 201, alta.text
    respuesta = api.cliente.patch(f"/api/grupos/{alta.json()['id']}", json={"metodo": metodo})
    assert respuesta.status_code == 422, (respuesta.status_code, respuesta.text)
    assert api.filas(
        "SELECT metodo, modo_de_coeficientes FROM grupo_de_reparto WHERE id = %s",
        (alta.json()["id"],),
    ) == [("coeficiente", "propios")]
