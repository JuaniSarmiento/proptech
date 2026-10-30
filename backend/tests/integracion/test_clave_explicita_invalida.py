"""pulido-2 (3d): una clave explícita que no cumple `^[a-z][a-z0-9_]{0,39}$`
(`compartido/parametros.py::_clave_valida`) se rechaza de punta a punta (HTTP +
base) para categorías y grupos: 422 que nombra el campo `clave`, sin repetir el
valor y sin escribir nada. Hasta ahora sólo estaba probada la derivación de la
clave (`test_categoria_sin_clave.py`) y el patrón como función pura."""

from typing import Any

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

# L-008: coincidencia completa y sólo ASCII; cada forma de romper el patrón.
CLAVES_INVALIDAS = [
    "Mayuscula",
    "1empieza_con_digito",
    "con espacio",
    "con-guion",
    "a" * 41,
    "ñandú",
    "abc\n",
]


def _cuerpo_categoria(clave: str) -> dict[str, Any]:
    return {"clave": clave, "nombre": "Reparaciones del borde"}


def _cuerpo_grupo(clave: str) -> dict[str, Any]:
    return {"clave": clave, "nombre": "Torre A", "metodo": "coeficiente"}


@pytest.mark.parametrize("clave", CLAVES_INVALIDAS)
@pytest.mark.parametrize(
    "ruta,conteo,cuerpo",
    [
        (
            "/categorias",
            "SELECT count(*) FROM categoria_de_gasto WHERE complejo_id=%s",
            _cuerpo_categoria,
        ),
        ("/grupos", "SELECT count(*) FROM grupo_de_reparto WHERE complejo_id=%s", _cuerpo_grupo),
    ],
)
def test_clave_explicita_invalida_da_422_en_clave_sin_repetir_el_valor(
    api_edificio: ApiEdificio, ruta: str, conteo: str, cuerpo: Any, clave: str
) -> None:
    api = api_edificio
    api.como("super_admin")
    antes = api.filas(conteo, (api.edificio,))

    respuesta = api.cliente.post(api.ruta(ruta), json=cuerpo(clave))

    assert respuesta.status_code == 422, respuesta.text
    assert "clave" in [e["loc"][-1] for e in respuesta.json()["detail"]]
    assert clave not in respuesta.text
    assert api.filas(conteo, (api.edificio,)) == antes


@pytest.mark.parametrize(
    "ruta,cuerpo",
    [("/categorias", _cuerpo_categoria), ("/grupos", _cuerpo_grupo)],
)
def test_clave_explicita_valida_en_el_limite_se_acepta(
    api_edificio: ApiEdificio, ruta: str, cuerpo: Any
) -> None:
    # Contraparte verde: el mismo camino acepta el borde válido (40 caracteres),
    # así el rechazo de arriba no es un 422 que cualquier clave explícita recibiría.
    api = api_edificio
    api.como("super_admin")
    respuesta = api.cliente.post(api.ruta(ruta), json=cuerpo("a" + "b" * 39))
    assert respuesta.status_code == 201, respuesta.text
