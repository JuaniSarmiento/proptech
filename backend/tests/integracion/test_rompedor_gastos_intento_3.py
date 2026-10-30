"""Pendiente de ejecutar contra PostgreSQL real."""

import pytest

from ._api_edificios import ApiEdificio
from .test_notas_de_credito import _crear_categoria_y_grupo, _crear_factura, _nota

pytestmark = pytest.mark.integracion


def test_periodo_factura_editada(api_edificio: ApiEdificio) -> None:
    categoria, grupo = _crear_categoria_y_grupo(api_edificio)
    factura = _crear_factura(api_edificio, categoria, grupo)
    nota = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura, "10.00", periodo="2026-11-01")
    )
    assert nota.status_code == 201, nota.text
    cambio = api_edificio.cliente.patch(f"/api/gastos/{factura}", json={"periodo": "2026-09-01"})
    assert cambio.status_code == 200, cambio.text
    lectura = api_edificio.cliente.get(f"/api/notas-de-credito/{nota.json()['id']}")
    assert lectura.status_code == 200, lectura.text
    assert lectura.json()["periodo_de_la_factura"] == "2026-09-01"
    assert lectura.json()["periodo"] == "2026-11-01"
