"""Ataque de cableado del rompedor (vuelta 2, F4; D8, D18, L-009): la spec
exige que la API anote el `request_id` en la sesión de PostgreSQL y D8 fija
`application_name=proptech-api` como nombre base de sus conexiones, gemelo de
`application_name=proptech-worker` del worker (`proptech_worker/ajustes.py`).
El test 3.4 lo prueba sobre un engine y una fábrica que arma el propio test;
acá se mira el engine que crea `crear_app()` de verdad.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

pytestmark = pytest.mark.integracion

RAIZ = Path(__file__).resolve().parents[3]


def test_el_engine_de_la_api_se_identifica_como_proptech_api(
    postgres_contenedor: PostgresContainer,
    monkeypatch: pytest.MonkeyPatch,
    roles_reales: None,
) -> None:
    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    monkeypatch.setenv("POSTGRES_HOST", postgres_contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(postgres_contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("POSTGRES_DB", postgres_contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "x")
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(RAIZ / "config" / "parametros.yaml"))

    from proptech_api.app import crear_app

    app = crear_app()
    with TestClient(app):
        with app.state.engine.connect() as conexion:
            consulta = text("SELECT current_setting('application_name')")
            nombre = conexion.execute(consulta).scalar_one()
    assert nombre == "proptech-api"
