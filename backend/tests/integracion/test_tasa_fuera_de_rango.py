"""Frente 3: escenarios de la spec que los tests de Codex dicen cubrir y
cuya aserción no prueba lo que el escenario dice."""

from typing import Any

import pytest

from ._api_edificios import ApiEdificio
from .test_configuracion_api import version

pytestmark = pytest.mark.integracion


@pytest.mark.parametrize("tasa", ["10.01", "-1.00", "-0.01", "-99999.99", "+11.00", "1000.00"])
@pytest.mark.parametrize("entrada", ["version", "alta"])
def test_tasa_fuera_de_rango_nombra_la_tasa_y_el_rango(
    api_edificio: ApiEdificio, tasa: str, entrada: str
) -> None:
    """`configuracion-versionada` > Tasa fuera de rango: "la respuesta es 422
    nombrando la tasa y el rango". El test de 6.3
    (`test_configuracion_invalida_da_422_antes_del_alcance_y_permiso_sin_valor`)
    sólo mira que `tasa_mensual` esté en `loc`; nunca el rango."""
    api = api_edificio
    api.como("super_admin")
    cuerpo = version(tasa_mensual=tasa)
    if entrada == "alta":
        cuerpo.pop("vigente_desde")
        respuesta = api.cliente.post(
            "/api/complejos",
            json={
                "nombre": "Nuevo",
                "provincia_id": "50",
                "departamento_id": "50007",
                "localidad_id": "50007010",
                "pisos": 4,
                "subsuelos": 1,
                "configuracion_inicial": cuerpo,
            },
        )
    else:
        respuesta = api.cliente.post(api.ruta("/configuracion/versiones"), json=cuerpo)
    assert respuesta.status_code == 422
    errores: list[dict[str, Any]] = respuesta.json()["detail"]
    de_la_tasa = [e for e in errores if e["loc"][-1] == "tasa_mensual"]
    assert de_la_tasa, errores
    assert any("0.00" in e["msg"] and "10.00" in e["msg"] for e in de_la_tasa), de_la_tasa
