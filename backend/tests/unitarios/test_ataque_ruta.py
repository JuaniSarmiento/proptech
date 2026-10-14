"""Ataque del rompedor (vuelta 2, F3): el campo `ruta` de `pedido_atendido`
filtra el valor de un parámetro de path (dato personal) en vez de la
plantilla, porque `_ruta_de` reconstruye la plantilla reemplazando el VALOR
sobre el path concreto: filtra si el valor es prefijo de otro segmento, o si
el convertidor (`int`, `uuid`) cambió el valor y éste ya no aparece en el
path.
"""

import io
import json
import logging
import uuid

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from proptech_api.seguimiento import MiddlewareSeguimiento
from proptech_core.compartido.logs import configurar_logs


def _cliente() -> tuple[TestClient, io.StringIO]:
    configurar_logs("api")
    app = FastAPI()
    app.add_middleware(MiddlewareSeguimiento)
    router = APIRouter(prefix="/api")

    @router.get("/personas/{dni}")
    def _por_dni(dni: str) -> dict[str, str]:
        return {"ok": "si"}

    @router.get("/unidades/{numero:int}")
    def _por_numero(numero: int) -> dict[str, str]:
        return {"ok": "si"}

    @router.get("/contratos/{id:uuid}")
    def _por_uuid(id: uuid.UUID) -> dict[str, str]:
        return {"ok": "si"}

    app.include_router(router)
    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        handler.stream = salida  # type: ignore[attr-defined]
    return TestClient(app), salida


def _ruta_logueada(salida: io.StringIO) -> str:
    eventos = [
        json.loads(linea)
        for linea in salida.getvalue().splitlines()
        if linea.strip() and json.loads(linea).get("evento") == "pedido_atendido"
    ]
    assert len(eventos) == 1
    return str(eventos[0]["ruta"])


@pytest.mark.parametrize(
    ("path", "plantilla", "dato"),
    [
        # el valor es prefijo de un segmento anterior: con el código viejo
        # (reemplazar `/{valor}` sobre el path concreto) "/pers" calza contra
        # el PRINCIPIO de "/personas" y pisa el segmento equivocado. "pers"
        # es además substring literal de "personas" en la plantilla estática:
        # por eso la prueba de no fuga es `ruta == plantilla` (más fuerte y
        # siempre correcta), nunca `dato not in ruta` (puede dar falso
        # positivo cuando el dato coincide con texto de un segmento fijo).
        ("/api/personas/pers", "/api/personas/{dni}", "pers"),
        # el convertidor int cambia el valor (0042 -> 42): no aparece en el path
        ("/api/unidades/0042", "/api/unidades/{numero}", "0042"),
        # el convertidor uuid normaliza a minúsculas: no aparece en el path
        (
            "/api/contratos/3F2C1A00-0001-4001-8001-0000000000AB",
            "/api/contratos/{id}",
            "3F2C1A00-0001-4001-8001-0000000000AB",
        ),
    ],
)
def test_ruta_logueada_es_la_plantilla_y_no_contiene_el_valor(
    path: str, plantilla: str, dato: str
) -> None:
    cliente, salida = _cliente()
    respuesta = cliente.get(path)
    assert respuesta.status_code == 200
    ruta = _ruta_logueada(salida)
    # Más fuerte que "dato not in ruta" (que da falso positivo si el dato
    # coincide con texto de un segmento fijo de la plantilla, como "pers" en
    # "personas"): si la ruta es EXACTAMENTE la plantilla estática, no puede
    # llevar el valor concreto de la variable salvo que ese valor también sea
    # texto fijo de la plantilla, que es irrelevante para la fuga.
    assert ruta == plantilla
    if dato not in plantilla:
        assert dato not in ruta
