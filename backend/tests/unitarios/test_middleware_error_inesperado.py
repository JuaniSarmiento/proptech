"""Tests del middleware de seguimiento ante un error no atrapado (D7, D13).
Cambio 1c, tarea 3.3.

Escenarios de `trazabilidad-y-logs`: Error inesperado; Error de un tercero con
datos en su mensaje. Lecciones: L-007.
"""

import io
import json
import logging

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError


def _app_con_captura(marcador: str) -> tuple[TestClient, io.StringIO]:
    from proptech_api.app import crear_app

    app = crear_app()

    @app.get("/api/_prueba/explota")
    def _explota() -> None:
        raise ValueError(f"dato personal: {marcador}")

    @app.get("/api/_prueba/explota-integridad")
    def _explota_integridad() -> None:
        raise IntegrityError(
            "INSERT INTO vecinos (email) VALUES (:email)",
            {"email": marcador},
            Exception("duplicado"),
        )

    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        handler.stream = salida  # type: ignore[attr-defined]

    return TestClient(app, raise_server_exceptions=False), salida


def test_error_inesperado_responde_500_sin_el_dato_y_sin_loguearlo() -> None:
    marcador = "dato-personal-f93a"
    cliente, salida = _app_con_captura(marcador)

    respuesta = cliente.get("/api/_prueba/explota")

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo.keys() == {"error", "request_id"}
    assert cuerpo["error"] == "interno"
    assert cuerpo["request_id"] == respuesta.headers["x-request-id"]

    assert marcador not in respuesta.text
    assert marcador not in salida.getvalue()

    eventos = [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]
    errores = [e for e in eventos if e.get("evento") == "error_inesperado"]
    assert len(errores) == 1
    assert errores[0]["tipo_error"] == "builtins.ValueError"
    assert errores[0]["nivel"] == "error"

    atendidos = [e for e in eventos if e.get("evento") == "pedido_atendido"]
    assert len(atendidos) == 1
    assert atendidos[0]["estado"] == 500


def test_error_de_integrity_error_con_parametro_marcado_no_aparece_en_la_salida() -> None:
    marcador = "vecino-marcado@ejemplo.invalid"
    cliente, salida = _app_con_captura(marcador)

    respuesta = cliente.get("/api/_prueba/explota-integridad")

    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "error": "interno",
        "request_id": respuesta.headers["x-request-id"],
    }
    assert marcador not in respuesta.text
    assert marcador not in salida.getvalue()

    eventos = [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]
    errores = [e for e in eventos if e.get("evento") == "error_inesperado"]
    assert len(errores) == 1
    assert errores[0]["tipo_error"] == "sqlalchemy.exc.IntegrityError"
