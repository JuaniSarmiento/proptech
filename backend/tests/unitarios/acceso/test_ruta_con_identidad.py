"""RF-B-2 (revisión final, 19/10/2026): `RutaConIdentidad` sólo tiene que
re-resolver la identidad para el error de PARSEO del cuerpo (D6: "en el
camino que parsea bien, la resolución habitual se ejecuta una sola vez"),
no para cualquier `HTTPException(400)` que levante el propio endpoint.

El defecto (`acceso.py:72-74`): el `except` miraba sólo `status_code == 400`,
sin mirar el `detail` — así que un endpoint que decide devolver 400 por un
motivo de dominio (no de parseo) hacía que la identidad se resolviera DOS
veces: una por FastAPI al armar la ruta, y otra por `con_identidad` al
"reparar" un parseo que en los hechos nunca falló.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from proptech_api.acceso import RutaConIdentidad, identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad


def _armar_app() -> tuple[FastAPI, dict[str, int]]:
    app = FastAPI()
    router = APIRouter(route_class=RutaConIdentidad)
    llamadas = {"n": 0}

    def identidad_contada() -> Identidad:
        llamadas["n"] += 1
        return Identidad(uuid4(), uuid4())

    @router.post("/prueba")
    def _ruta(_identidad: Identidad = Depends(identidad_actual)) -> None:
        raise HTTPException(status_code=400, detail="motivo de dominio, no de parseo")

    app.include_router(router)
    app.dependency_overrides[identidad_actual] = identidad_contada
    return app, llamadas


def test_400_de_dominio_con_identidad_valida_la_resuelve_una_sola_vez() -> None:
    app, llamadas = _armar_app()
    cliente = TestClient(app, raise_server_exceptions=False)
    respuesta = cliente.post("/prueba", json={})
    assert respuesta.status_code == 400
    assert llamadas["n"] == 1, f"identidad_actual se resolvió {llamadas['n']} veces, se esperaba 1"


def test_400_de_parseo_de_verdad_sigue_resolviendo_identidad() -> None:
    """Control (L-019): si el arreglo dejara de re-resolver TAMBIÉN para el
    parseo real, este test (que ya pasaba antes del arreglo) se rompería.
    `content=b"\\xff"` con Content-Type JSON produce el 400 genérico de
    FastAPI ("There was an error parsing the body"), no uno del endpoint."""
    app = FastAPI()
    router = APIRouter(route_class=RutaConIdentidad)

    @router.post("/prueba")
    def _ruta(_identidad: Identidad = Depends(identidad_actual)) -> None:  # pragma: no cover
        raise AssertionError("nunca se llega: el cuerpo no parsea")

    app.include_router(router)
    app.dependency_overrides.pop(identidad_actual, None)
    cliente = TestClient(app, raise_server_exceptions=False)
    respuesta = cliente.post(
        "/prueba", content=b"\xff", headers={"Content-Type": "application/json"}
    )
    assert respuesta.status_code == 401, respuesta.text
