"""Tests del middleware de seguimiento: asigna o valida el `request_id`, lo
devuelve en `X-Request-ID` y loguea `pedido_atendido` (D8). Cambio 1c, 3.2.

Escenarios de `trazabilidad-y-logs`: Pedido sin número de seguimiento; Número
de seguimiento malicioso; Línea de un pedido atendido; Query string con un dato
personal.
"""

import io
import json
import logging
import re

from fastapi.testclient import TestClient

PATRON_UUID = re.compile(r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


def _app_con_captura() -> tuple[TestClient, io.StringIO]:
    from proptech_api.app import crear_app

    app = crear_app()

    @app.get("/api/_prueba/eco-hilo")
    def _eco_hilo() -> dict[str, str | None]:
        # Endpoint `def`: FastAPI lo corre en el pool de hilos. Si la
        # ContextVar no llega al hilo, esto da `None`.
        from proptech_core.compartido.seguimiento import request_id_actual

        return {"request_id_visto": request_id_actual.get()}

    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        handler.stream = salida  # type: ignore[attr-defined]

    return TestClient(app), salida


def _lineas_json(salida: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]


def test_sin_encabezado_genera_un_uuid_y_lo_devuelve() -> None:
    cliente, salida = _app_con_captura()
    respuesta = cliente.get("/api/salud")

    request_id = respuesta.headers["x-request-id"]
    assert PATRON_UUID.match(request_id)

    eventos = [linea for linea in _lineas_json(salida) if linea.get("evento") == "pedido_atendido"]
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento["request_id"] == request_id
    assert evento["metodo"] == "GET"
    assert evento["ruta"] == "/api/salud"
    assert evento["estado"] == respuesta.status_code
    assert isinstance(evento["duracion_ms"], int)


def test_request_id_invalido_se_descarta_y_no_aparece_en_los_logs() -> None:
    cliente, salida = _app_con_captura()
    valor_malicioso = "<script>alert(1)</script>"
    respuesta = cliente.get("/api/salud", headers={"X-Request-ID": valor_malicioso})

    request_id_devuelto = respuesta.headers["x-request-id"]
    assert PATRON_UUID.match(request_id_devuelto)
    assert request_id_devuelto != valor_malicioso

    assert valor_malicioso not in salida.getvalue()


def test_query_string_con_un_dato_personal_no_aparece_en_los_logs() -> None:
    cliente, salida = _app_con_captura()
    cliente.get("/api/salud?email=vecino@ejemplo.invalid")

    eventos = [linea for linea in _lineas_json(salida) if linea.get("evento") == "pedido_atendido"]
    assert len(eventos) == 1, "no se logueó pedido_atendido: el test no prueba nada sin eso"
    assert "vecino@ejemplo.invalid" not in salida.getvalue()
    assert "email=" not in salida.getvalue()


def test_ruta_sin_coincidencia_loguea_el_path_truncado_sin_query_string() -> None:
    cliente, salida = _app_con_captura()
    cliente.get("/api/no-existe-esta-ruta?clave=secreta")

    eventos = [linea for linea in _lineas_json(salida) if linea.get("evento") == "pedido_atendido"]
    assert len(eventos) == 1
    assert eventos[0]["ruta"] == "/api/no-existe-esta-ruta"
    assert eventos[0]["estado"] == 404


def test_endpoint_def_ve_el_request_id_la_contextvar_llega_al_hilo() -> None:
    cliente, _salida = _app_con_captura()
    respuesta = cliente.get("/api/_prueba/eco-hilo")
    request_id_cabecera = respuesta.headers["x-request-id"]
    assert respuesta.json()["request_id_visto"] == request_id_cabecera


def test_dos_x_request_id_se_rechazan_como_en_la_web() -> None:
    """Ataque del rompedor (vuelta 2, F9; L-009 gemelo de la web): con dos
    `X-Request-ID`, la API (Starlette `Headers.get`) tomaba el PRIMERO,
    mientras que la web (el `Headers` del fetch del navegador/Node) los une
    con coma y los dos quedan rechazados (`requestIdDe` genera uno nuevo). La
    spec pide que la API rechace igual que la web: aceptar y rechazar
    exactamente lo mismo."""
    cliente, salida = _app_con_captura()
    primero = "11111111-1111-4111-8111-111111111111"
    segundo = "22222222-2222-4222-8222-222222222222"
    encabezados = [("X-Request-ID", primero), ("X-Request-ID", segundo)]
    respuesta = cliente.get("/api/salud", headers=encabezados)

    request_id_devuelto = respuesta.headers["x-request-id"]
    assert PATRON_UUID.match(request_id_devuelto)
    # Ninguno de los dos valores enviados: se rechazan los dos, no se toma
    # "el primero que llegó" (eso es lo que hacía la API y la web no).
    assert request_id_devuelto not in (primero, segundo)
    assert primero not in salida.getvalue()
    assert segundo not in salida.getvalue()
