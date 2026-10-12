"""3.4: adaptador pydantic de Dinero — rechaza número JSON, acepta texto."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from proptech_core.compartido.dinero import Dinero


class _ModeloConMonto(BaseModel):
    monto: Dinero


def _app() -> FastAPI:
    app = FastAPI()

    @app.post("/monto")
    def recibir(datos: _ModeloConMonto) -> dict[str, str]:
        return {"monto": datos.monto.a_texto()}

    return app


def test_rechaza_numero_json_float() -> None:
    cliente = TestClient(_app())
    respuesta = cliente.post("/monto", json={"monto": 20000.0})
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert any("monto" in str(e.get("loc")) for e in cuerpo["detail"])


def test_rechaza_numero_json_entero() -> None:
    cliente = TestClient(_app())
    respuesta = cliente.post("/monto", json={"monto": 20000})
    assert respuesta.status_code == 422


def test_acepta_texto_valido() -> None:
    cliente = TestClient(_app())
    respuesta = cliente.post("/monto", json={"monto": "20000.00"})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"monto": "20000.00"}


def test_serializa_a_texto() -> None:
    cliente = TestClient(_app())
    respuesta = cliente.post("/monto", json={"monto": "5"})
    assert respuesta.json() == {"monto": "5.00"}


def test_modelo_rechaza_texto_invalido() -> None:
    cliente = TestClient(_app())
    respuesta = cliente.post("/monto", json={"monto": "1,50"})
    assert respuesta.status_code == 422
