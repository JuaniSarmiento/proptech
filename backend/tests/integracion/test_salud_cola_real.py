"""Integración: `/api/salud` y el arranque con Redis real (D4, L-001). Cambio
1c, tarea 4.7. Contenedor de Redis propio del test (nunca el de sesión ni el
de Compose, L-006); el pausado se despausa en un `finally`.

Escenarios: `entorno-de-ejecucion`, La cola no responde; `cola-de-trabajos`,
La API arranca sin Redis. Lecciones: L-001.
"""

import contextlib
import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

pytestmark = pytest.mark.integracion

#: Contraseña sólo de este contenedor de test, nunca una credencial real.
_PASSWORD = "prueba-salud-cola-no-real"


@pytest.fixture
def contenedor_redis_propio() -> Iterator[DockerContainer]:
    from ..conftest import IMAGEN_REDIS_PARA_TESTS

    contenedor = (
        DockerContainer(IMAGEN_REDIS_PARA_TESTS)
        .with_command(f"redis-server --requirepass {_PASSWORD} --enable-debug-command yes")
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    contenedor.start()
    try:
        yield contenedor
    finally:
        # El test puede haberlo detenido/eliminado a mano (caso "Redis
        # detenido"); un segundo stop/remove sobre un contenedor que ya no
        # existe levanta un error de la API de Docker que acá no importa.
        with contextlib.suppress(Exception):
            contenedor.stop()


def _configurar_entorno(
    monkeypatch: pytest.MonkeyPatch,
    postgres: PostgresContainer,
    redis_host: str,
    redis_port: int,
) -> None:
    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    monkeypatch.setenv("POSTGRES_HOST", postgres.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(postgres.get_exposed_port(5432)))
    # El rol real de la app (D1, D3, tarea 2.2), que `roles_reales` ya creó.
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("POSTGRES_DB", postgres.dbname)
    monkeypatch.setenv("REDIS_HOST", redis_host)
    monkeypatch.setenv("REDIS_PORT", str(redis_port))
    monkeypatch.setenv("REDIS_PASSWORD", _PASSWORD)


def test_redis_pausado_responde_503_cola_sin_conexion_en_menos_de_4s(
    postgres_contenedor: PostgresContainer,
    contenedor_redis_propio: DockerContainer,
    monkeypatch: pytest.MonkeyPatch,
    roles_reales: None,
) -> None:
    _configurar_entorno(
        monkeypatch,
        postgres_contenedor,
        contenedor_redis_propio.get_container_host_ip(),
        int(contenedor_redis_propio.get_exposed_port(6379)),
    )
    from proptech_api.app import crear_app

    app = crear_app()
    contenedor_docker = contenedor_redis_propio.get_wrapped_container()
    contenedor_docker.pause()
    try:
        with TestClient(app) as cliente:
            inicio = time.monotonic()
            respuesta = cliente.get("/api/salud")
            duracion = time.monotonic() - inicio
    finally:
        contenedor_docker.unpause()

    assert respuesta.status_code == 503
    assert respuesta.json()["cola"] == "sin_conexion"
    assert duracion < 4, f"tardó {duracion:.2f}s"


def test_redis_detenido_responde_503_cola_sin_conexion_en_menos_de_4s(
    postgres_contenedor: PostgresContainer,
    contenedor_redis_propio: DockerContainer,
    monkeypatch: pytest.MonkeyPatch,
    roles_reales: None,
) -> None:
    _configurar_entorno(
        monkeypatch,
        postgres_contenedor,
        contenedor_redis_propio.get_container_host_ip(),
        int(contenedor_redis_propio.get_exposed_port(6379)),
    )
    contenedor_redis_propio.stop()

    from proptech_api.app import crear_app

    app = crear_app()
    with TestClient(app) as cliente:
        inicio = time.monotonic()
        respuesta = cliente.get("/api/salud")
        duracion = time.monotonic() - inicio

    assert respuesta.status_code == 503
    assert respuesta.json()["cola"] == "sin_conexion"
    assert duracion < 4, f"tardó {duracion:.2f}s"


def test_crear_app_expone_la_cola_cableada_y_arranca_sin_intentar_conectar(
    postgres_contenedor: PostgresContainer,
    monkeypatch: pytest.MonkeyPatch,
    roles_reales: None,
) -> None:
    """Redis inalcanzable (IP privada sin ruta, L-001): `crear_app()` no se
    cuelga al armar la cola (pool perezoso, D4) y `/api/salud` responde."""
    from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    monkeypatch.setenv("POSTGRES_HOST", postgres_contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(postgres_contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("POSTGRES_DB", postgres_contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "10.255.255.1")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_PASSWORD", _PASSWORD)

    from proptech_api.app import crear_app
    from proptech_core.compartido.cola import AdaptadorColaArq

    inicio = time.monotonic()
    app = crear_app()
    duracion_arranque = time.monotonic() - inicio
    assert duracion_arranque < 1, (
        f"crear_app() tardó {duracion_arranque:.2f}s: no debería intentar conectar a Redis"
    )
    assert isinstance(app.state.cola, AdaptadorColaArq)

    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json()["cola"] == "sin_conexion"
