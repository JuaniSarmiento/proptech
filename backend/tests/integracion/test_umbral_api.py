"""D-114.1: herencia por fecha y contrato de alta/versiones."""

from typing import Any

import pytest

from ._api_edificios import ApiEdificio
from .test_configuracion_api import CONFIGURACION

pytestmark = pytest.mark.integracion


def test_herencia_inmediatamente_anterior(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    alta = api.cliente.post(
        "/api/complejos",
        json={
            "nombre": "Herencia ficticia",
            "localidad": "Mendoza",
            "configuracion_inicial": {**CONFIGURACION, "umbral_saldo_chico": "300.00"},
        },
    )
    assert alta.status_code == 201, alta.text
    ruta = f"/api/complejos/{alta.json()['id']}/configuracion/versiones"
    casos = [
        ("2026-12-01", "700.00", "700.00"),
        ("2027-01-01", None, "700.00"),
        ("2026-11-15", None, "300.00"),
        ("2027-02-01", "0.00", "0.00"),
        ("2027-03-01", "750.00", "750.00"),
    ]
    for fecha, umbral, esperado in casos:
        cuerpo = {**CONFIGURACION, "vigente_desde": fecha}
        if umbral is not None or fecha == "2027-01-01":
            cuerpo["umbral_saldo_chico"] = umbral
        r = api.cliente.post(ruta, json=cuerpo)
        assert r.status_code == 201, r.text
        versiones = api.cliente.get(ruta).json()
        nueva = next(v for v in versiones if v["vigente_desde"] == fecha)
        assert nueva["umbral_saldo_chico"] == esperado


@pytest.mark.parametrize("umbral", [500, "-1.00", "1.001", "abc"])
@pytest.mark.parametrize("alta", [False, True])
def test_umbral_invalido_no_escribe(api_edificio: ApiEdificio, umbral: Any, alta: bool) -> None:
    api = api_edificio
    config = {**CONFIGURACION, "umbral_saldo_chico": umbral}
    cuerpo = (
        {"nombre": "Ficticio", "localidad": "Mendoza", "configuracion_inicial": config}
        if alta
        else {**config, "vigente_desde": "2027-01-01"}
    )
    ruta = "/api/complejos" if alta else api.ruta("/configuracion/versiones")
    r = api.cliente.post(ruta, json=cuerpo)
    assert r.status_code == 422, r.text
    assert any(e["loc"][-1] == "umbral_saldo_chico" for e in r.json()["detail"])
    assert all("input" not in e and "ctx" not in e for e in r.json()["detail"])


@pytest.mark.parametrize(
    "umbral,esperado", [(None, "500.00"), ("0.00", "0.00"), ("750.00", "750.00")]
)
def test_alta_con_configuracion_inicial(
    api_edificio: ApiEdificio, umbral: str | None, esperado: str
) -> None:
    config = dict(CONFIGURACION)
    if umbral is not None:
        config["umbral_saldo_chico"] = umbral
    api = api_edificio
    r = api.cliente.post(
        "/api/complejos",
        json={"nombre": "Nuevo ficticio", "localidad": "Mendoza", "configuracion_inicial": config},
    )
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    version = api.cliente.get(f"/api/complejos/{vid}/configuracion").json()
    assert version["umbral_saldo_chico"] == esperado
