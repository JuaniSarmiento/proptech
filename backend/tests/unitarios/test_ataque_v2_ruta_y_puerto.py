"""Vuelta 2: F3 cierra sólo si el prefijo vive en el router que declara la
ruta (`path_format` no incluye el prefijo de `include_router(prefix=...)` ni
el de un router padre en FastAPI 0.143); F10 no se aplicó al gemelo
`POSTGRES_PORT` (L-009)."""

import io
import json
import logging

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from proptech_api.seguimiento import MiddlewareSeguimiento
from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida
from proptech_core.compartido.logs import configurar_logs


def _ruta(app: FastAPI, path: str) -> str:
    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        handler.stream = salida  # type: ignore[attr-defined]
    assert TestClient(app).get(path).status_code == 200
    eventos = [
        json.loads(linea)
        for linea in salida.getvalue().splitlines()
        if '"pedido_atendido"' in linea
    ]
    return str(eventos[0]["ruta"])


def _app(forma: str) -> FastAPI:
    configurar_logs("api")
    app = FastAPI()
    app.add_middleware(MiddlewareSeguimiento)
    hijo = APIRouter()

    @hijo.get("/unidades/{unidad}")
    def _u(unidad: str) -> dict[str, str]:
        return {}

    if forma == "prefix_en_include":
        app.include_router(hijo, prefix="/api")
    else:  # router padre, el patrón de "routers por dominio"
        padre = APIRouter(prefix="/api")
        padre.include_router(hijo)
        app.include_router(padre)
    return app


@pytest.mark.parametrize("forma", ["prefix_en_include", "router_anidado"])
def test_la_ruta_logueada_lleva_el_prefijo_completo(forma: str) -> None:
    assert _ruta(_app(forma), "/api/unidades/u-7") == "/api/unidades/{unidad}"


_BASE = {
    "POSTGRES_HOST": "h",
    "POSTGRES_USER": "u",
    "POSTGRES_PASSWORD": "p",
    "POSTGRES_DB": "d",
    "REDIS_HOST": "r",
    "REDIS_PORT": "6379",
    "REDIS_PASSWORD": "x",
}


@pytest.mark.parametrize("valor", ["5432\n", " 5432", "5_432", "+5432", "5432.0"])
def test_postgres_port_rechaza_formas_no_canonicas(
    valor: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    for clave, v in _BASE.items():
        monkeypatch.setenv(clave, v)
    monkeypatch.setenv(
        "PROPTECH_PARAMETROS",
        str(Path(__file__).resolve().parents[3] / "config" / "parametros.yaml"),
    )
    monkeypatch.setenv("POSTGRES_PORT", valor)
    with pytest.raises(ConfiguracionInvalida):
        Configuracion()
