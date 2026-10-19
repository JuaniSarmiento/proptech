"""El 422 saneado (`manejador_422`) nunca repite ni un fragmento del valor
que mandó el cliente, en ningún `type` de error de pydantic (R3A-5, D6,
L-007).

`manejador_422` ya quitaba `input` y `ctx`, pero copiaba `msg` tal cual: para
un UUID mal formado, pydantic arma `msg` con el carácter rechazado
("invalid character: found `X` at 0"), y para otros tipos (longitud,
formato) puede llevar un fragmento del valor o su tamaño. `_motivo`
(`cuerpos.py`) sólo deja pasar el `msg` de `type == "value_error"` — los
`ValueError` que este cambio escribe a mano, ya auditados para nunca repetir
el valor (L-002) — y blanquea todo lo demás con un motivo genérico por
`type`, en vez de confiar tipo por tipo en lo que pydantic generó.
"""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

MARCA = "Ж"


def test_uuid_invalido_en_el_cuerpo_no_aparece_en_el_422(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    api.como("titular")
    respuestas = [
        api.cliente.post(
            api.ruta("/grupos"),
            json={
                "clave": "pileta",
                "nombre": "Pileta",
                "metodo": "coeficiente",
                "unidades": [{"unidad_id": MARCA + "secreto"}],
            },
        ),
        api.cliente.put(api.ruta("/categorias/orden"), json={"orden": [MARCA + "secreto"]}),
    ]
    for respuesta in respuestas:
        assert respuesta.status_code == 422
        assert MARCA not in respuesta.text, respuesta.text


def test_rol_invalido_en_la_asignacion_tampoco_aparece_en_el_422(api_edificio: ApiEdificio) -> None:
    """Family, no ejemplo: un `type` distinto (`literal_error`, de
    `CuerpoAsignacion.rol`) también pasa por `_motivo`, no por el `msg` que
    arma pydantic — aunque ESE `msg` en particular sólo nombra los valores
    permitidos, no el que mandó el cliente."""
    api = api_edificio
    api.como("titular")
    respuesta = api.cliente.post(
        api.ruta("/asignaciones"),
        json={"persona_id": str(api.personas["ver"]), "rol": MARCA + "secreto"},
    )
    assert respuesta.status_code == 422
    assert MARCA not in respuesta.text, respuesta.text
    assert respuesta.json()["detail"][0]["msg"] == "valor inválido (literal_error)"


def test_mensaje_propio_de_un_validador_nuestro_si_se_conserva(api_edificio: ApiEdificio) -> None:
    """Control del fix (L-019): el `ValueError` que escribimos a mano
    (`type=value_error`, p.ej. el de `recortado_sin_control`) no se tapa —
    si `_motivo` blanqueara TODO, este mensaje también desaparecería."""
    api = api_edificio
    api.como("titular")
    respuesta = api.cliente.post(
        api.ruta("/unidades"),
        json={
            "identificador": "A\u0000B",
            "tipo": "departamento",
            "piso": "1",
            "coeficiente": "0.100000",
            "superficie_m2": "60.00",
        },
    )
    assert respuesta.status_code == 422
    assert (
        respuesta.json()["detail"][0]["msg"]
        == "Value error, no puede contener caracteres de control, invisibles o no representables"
    )
