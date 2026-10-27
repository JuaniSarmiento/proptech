"""D9: identidad, petición y atomicidad contra PostgreSQL real."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from proptech_core.complejos.aplicacion import unidades

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def alta(
    api: ApiEdificio, identificador: str = "Nueva ficticia", coeficiente: str = "0.050000"
) -> str:
    r = api.cliente.post(
        api.ruta("/unidades"),
        json={
            "identificador": identificador,
            "tipo": "departamento",
            "piso": "1",
            "coeficiente": coeficiente,
            "superficie_m2": "60.00",
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def filas(api: ApiEdificio, uid: str, evento: str) -> list[Any]:
    return api.filas(
        "SELECT persona_id,request_id,detalle FROM auditoria WHERE entidad_id=%s AND accion=%s",
        (uid, evento),
    )


def test_alta_audita_coeficiente(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    uid = alta(api, coeficiente="0.080000")
    registros = filas(api, uid, "crear_unidad")
    assert len(registros) == 1
    assert registros[0][0] == api.personas["super_admin"]
    assert registros[0][2]["coeficiente"] == {"anterior": None, "nuevo": "0.080000"}
    assert registros[0][2]["complejo_id"] == str(api.edificio)


def test_edicion_normalizada_solo_guarda_cambios(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    uid = alta(api)
    ruta = f"/api/unidades/{uid}"
    r = api.cliente.patch(ruta, json={"coeficiente": "0.05", "piso": "1"})
    assert r.status_code == 200
    assert filas(api, uid, "editar_unidad") == []
    r = api.cliente.patch(ruta, json={"coeficiente": "0.060000", "piso": "SS1"})
    assert r.status_code == 200
    registros = filas(api, uid, "editar_unidad")
    assert len(registros) == 1
    detalle = registros[0][2]
    assert detalle == {
        "complejo_id": str(api.edificio),
        "campos": ["coeficiente", "piso"],
        "coeficiente": {"anterior": "0.050000", "nuevo": "0.060000"},
    }
    assert "SS1" not in str(detalle)


def test_conflicto_no_deja_auditoria(api_edificio: ApiEdificio) -> None:
    api = api_edificio
    uid = alta(api)
    duplicada = api.cliente.get(f"/api/unidades/{api.unidad}").json()["identificador"]
    antes = api.cliente.get(f"/api/unidades/{uid}").json()
    r = api.cliente.patch(f"/api/unidades/{uid}", json={"identificador": duplicada})
    assert r.status_code == 409
    assert api.cliente.get(f"/api/unidades/{uid}").json() == antes
    assert filas(api, uid, "editar_unidad") == []


def test_falla_auditoria_revierte_y_no_filtra(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = api_edificio
    uid = alta(api)
    antes = api.cliente.get(f"/api/unidades/{uid}").json()
    invocado = []

    def fallar(*args: Any, **kwargs: Any) -> None:
        invocado.append(True)
        raise RuntimeError("MARCADOR_AUDITORIA_PRIVADO")

    monkeypatch.setattr(unidades, "registrar", fallar)
    cliente = TestClient(api.app, raise_server_exceptions=False)
    try:
        r = cliente.patch(f"/api/unidades/{uid}", json={"piso": "SS1"})
    finally:
        cliente.close()
    assert invocado == [True]
    assert r.status_code == 500
    assert "PRIVADO" not in r.text
    assert api.cliente.get(f"/api/unidades/{uid}").json() == antes
    assert filas(api, uid, "editar_unidad") == []
