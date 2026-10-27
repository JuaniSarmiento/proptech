"""2.5: las tres rutas de lectura de Georef — con sesión, sin ella (401) y
con un padre inexistente (404). No dependen del edificio ni del rol
(cualquier identidad autenticada las puede leer)."""

import pytest

from proptech_api.acceso import identidad_actual

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def test_provincias_con_sesion(api_edificio: ApiEdificio) -> None:
    respuesta = api_edificio.cliente.get("/api/georef/provincias")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 24
    mendoza = next(p for p in cuerpo if p["id"] == "50")
    assert mendoza["nombre"] == "Mendoza"


def test_departamentos_de_mendoza(api_edificio: ApiEdificio) -> None:
    respuesta = api_edificio.cliente.get("/api/georef/provincias/50/departamentos")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 18
    assert all(isinstance(d["id"], str) for d in cuerpo)


def test_localidades_de_godoy_cruz(api_edificio: ApiEdificio) -> None:
    respuesta = api_edificio.cliente.get("/api/georef/departamentos/50021/localidades")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) > 0


def test_provincia_inexistente_404(api_edificio: ApiEdificio) -> None:
    respuesta = api_edificio.cliente.get("/api/georef/provincias/99/departamentos")
    assert respuesta.status_code == 404


def test_departamento_inexistente_404(api_edificio: ApiEdificio) -> None:
    respuesta = api_edificio.cliente.get("/api/georef/departamentos/99999/localidades")
    assert respuesta.status_code == 404


def test_sin_sesion_401(api_edificio: ApiEdificio) -> None:
    api_edificio.app.dependency_overrides.pop(identidad_actual)
    respuesta = api_edificio.cliente.get("/api/georef/provincias")
    assert respuesta.status_code == 401
