"""D7 (tarea 4.5, y la mitad API de 4.2): desactivar/reactivar un grupo
parcial; "Generales" lo rechaza; sin ruta de borrado; un grupo desactivado
no reclama unidades en la puesta a punto."""

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def _grupo_parcial(api: ApiEdificio) -> str:
    r = api.cliente.post(
        api.ruta("/grupos"),
        json={"nombre": "Pileta", "metodo": "coeficiente"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def test_desactivar_un_grupo_parcial(api_edificio: ApiEdificio) -> None:
    """Escenario "Desactivar un grupo parcial"."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    r = api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": False})
    assert r.status_code == 200, r.text
    disponibles = api.cliente.get(api.ruta("/grupos?solo_activos=true")).json()
    assert grupo_id not in [g["id"] for g in disponibles]
    todos = api.cliente.get(api.ruta("/grupos")).json()
    grupo = next(g for g in todos if g["id"] == grupo_id)
    assert grupo["activo"] is False


def test_reactivar(api_edificio: ApiEdificio) -> None:
    """Escenario "Reactivar"."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": False})
    r = api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": True})
    assert r.status_code == 200, r.text
    disponibles = api.cliente.get(api.ruta("/grupos?solo_activos=true")).json()
    assert grupo_id in [g["id"] for g in disponibles]


def test_borrar_no_tiene_ruta(api_edificio: ApiEdificio) -> None:
    """Escenario "Borrar": no existe ruta que lo permita."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    r = api.cliente.delete(f"/api/grupos/{grupo_id}")
    assert r.status_code == 405
    assert api.cliente.get(api.ruta("/grupos")).json()


def test_desactivar_generales_da_422(api_edificio: ApiEdificio) -> None:
    """Escenario "Desactivar Generales" (D7, tarea 4.2, mitad API)."""
    api = api_edificio
    api.como("super_admin")
    generales = next(g for g in api.cliente.get(api.ruta("/grupos")).json() if g["es_generales"])
    r = api.cliente.patch(f"/api/grupos/{generales['id']}", json={"activo": False})
    assert r.status_code == 422
    assert next(
        g for g in api.cliente.get(api.ruta("/grupos")).json() if g["es_generales"]
    )["activo"] is True


def test_grupo_desactivado_sin_unidades_no_bloquea_la_puesta_a_punto(
    api_edificio: ApiEdificio,
) -> None:
    """Escenario "Un grupo desactivado no reclama unidades"."""
    api = api_edificio
    api.como("super_admin")
    grupo_id = _grupo_parcial(api)
    resumen_antes = api.cliente.get(api.ruta("/resumen")).json()
    assert resumen_antes["pasos"]["grupos"] == "falta"
    api.cliente.patch(f"/api/grupos/{grupo_id}", json={"activo": False})
    resumen_despues = api.cliente.get(api.ruta("/resumen")).json()
    assert resumen_despues["pasos"]["grupos"] == "hecho"
