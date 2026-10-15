"""Test de integración: la base se congela con una conexión ya abierta en el
pool (D18, L-006). Cambio 1c, tarea 3.6 (parte 3 de 3, el caso que
`connect_timeout` no cubre).

Escenario de `entorno-de-ejecucion`: La base se congela con una conexión
abierta. Usa un contenedor propio (nunca el de sesión de `conftest.py`,
L-006): lo pausamos a propósito.
"""

import time
from collections.abc import Iterator

import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_api.salud import _verificador_con_engine
from proptech_core.compartido.base_de_datos import crear_engine
from proptech_core.compartido.configuracion import Configuracion

pytestmark = pytest.mark.integracion


@pytest.fixture
def contenedor_propio() -> Iterator[PostgresContainer]:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    # Usuario con el patrón proptech_* (D1, D3, cambio 2a): ver postgres_contenedor
    # de sesión en tests/conftest.py.
    contenedor = PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username="proptech_test",
        password="proptech_test",  # noqa: S106 (contraseña de este contenedor de test, nunca real)
    )
    with contenedor as iniciado:
        yield iniciado


#: Rol real de la app (D1, D2, tarea 2.2) sobre el contenedor propio de este
#: archivo (nunca el de sesión, L-006): distinto del superusuario del contenedor.
_APP_USER = "proptech_app"
_APP_PASSWORD = "clave-app-no-real"


def _crear_rol_de_la_app(contenedor: PostgresContainer) -> None:
    import os
    import subprocess
    import sys

    from ..conftest import RAIZ

    entorno = {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": "proptech_migrador",
        "POSTGRES_MIGRADOR_PASSWORD": "clave-migrador-no-real",
        "POSTGRES_APP_USER": _APP_USER,
        "POSTGRES_APP_PASSWORD": _APP_PASSWORD,
        "POSTGRES_RESPALDO_USER": "proptech_respaldo",
        "POSTGRES_RESPALDO_PASSWORD": "clave-respaldo-no-real",
    }
    subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ / "backend",
        env=entorno,
        check=True,
        capture_output=True,
        text=True,
    )


def _configuracion_para(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> Configuracion:
    _crear_rol_de_la_app(contenedor)
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", _APP_USER)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", _APP_PASSWORD)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    return Configuracion()


def test_base_congelada_con_conexion_abierta_responde_degradado_en_menos_de_3s(
    contenedor_propio: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> None:
    configuracion = _configuracion_para(contenedor_propio, monkeypatch)
    engine = crear_engine(configuracion)
    verificar = _verificador_con_engine(engine)

    try:
        # Primero, una conexión sana: queda devuelta (idle) en el pool.
        assert verificar() is True

        contenedor_docker = contenedor_propio.get_wrapped_container()
        contenedor_docker.pause()
        try:
            inicio = time.monotonic()
            # `connect_timeout` no cubre esto: la conexión ya estaba
            # establecida antes de pausar. El plazo propio del verificador
            # (D18) es lo único que lo acota.
            assert verificar() is False
            duracion = time.monotonic() - inicio
            assert duracion < 3, f"tardó {duracion:.2f}s, debía responder en menos de 3s"
        finally:
            contenedor_docker.unpause()

        # Despausada: el pedido siguiente responde ok (otra conexión del
        # pool, o una nueva; la que quedó colgada en el hilo anterior no se
        # vuelve a usar).
        assert verificar() is True
    finally:
        engine.dispose()
