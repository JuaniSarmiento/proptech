"""Test de integración de base caída durante el trabajo (D3, D18). Cambio
1c, tarea 5.8.

PostgreSQL propio del test (L-006, nunca el de sesión): pausado antes de
encolar y despausado en un `finally` antes de que corra el segundo intento,
para que la tarea se reintente como pasajera y termine registrando la clave
una sola vez.

Escenario de `cola-de-trabajos`: Base caída durante el trabajo. Lecciones:
L-001, L-006.
"""

import subprocess
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import arq
import arq.worker
import pytest
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_application_name,
)
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.reintentos import PoliticaReintentos
from proptech_worker.tareas import NOMBRE_TAREA_DE_PRUEBA

pytestmark = pytest.mark.integracion

_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)
_LIMITE_S = 5.0

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


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


def _migrar_a_head(contenedor: PostgresContainer) -> None:
    import os

    entorno = {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_MIGRADOR_USER": contenedor.username,
        "POSTGRES_MIGRADOR_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
    }
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        check=True,
        capture_output=True,
        text=True,
    )


def _configuracion_para(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> Configuracion:
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    monkeypatch.setenv("POSTGRES_APP_USER", contenedor.username)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", contenedor.password)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    # Más corto que el default (2s): la cota de este test (D18, L-001).
    monkeypatch.setenv("DB_CONNECT_TIMEOUT_S", "1")
    return Configuracion()


@pytest.mark.anyio
async def test_base_caida_en_el_primer_intento_se_reintenta_y_registra_una_vez(
    ajustes_del_worker: Any,
    contenedor_propio: PostgresContainer,
    monkeypatch: pytest.MonkeyPatch,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    _migrar_a_head(contenedor_propio)
    configuracion_test = _configuracion_para(contenedor_propio, monkeypatch)

    async def _on_startup_de_test(ctx: dict[str, Any]) -> None:
        engine = crear_engine(
            configuracion_test, connect_args={"application_name": "proptech-worker"}
        )
        fabrica = crear_fabrica_de_sesiones(engine)
        registrar_application_name(fabrica, "proptech-worker")
        ctx["engine"] = engine
        ctx["fabrica_de_sesiones"] = fabrica
        ctx["politica"] = _POLITICA_RAPIDA

    kwargs: dict[str, Any] = dict(arq.worker.get_kwargs(ajustes_del_worker.AjustesDelWorker))
    kwargs["on_startup"] = _on_startup_de_test
    kwargs["queue_name"] = nombre_cola

    clave = f"worker-base-caida-{uuid.uuid4()}"
    request_id = str(uuid.uuid4())
    await cola.encolar(NOMBRE_TAREA_DE_PRUEBA, clave=clave, request_id=request_id, fallar_veces=0)

    contenedor_docker = contenedor_propio.get_wrapped_container()
    contenedor_docker.pause()

    pausado = True
    worker = arq.Worker(
        **kwargs, burst=True, handle_signals=False, poll_delay=0.01, max_burst_jobs=10
    )
    try:
        import asyncio

        inicio = time.monotonic()
        tarea = asyncio.ensure_future(worker.async_run())
        # Dejar que el primer intento choque contra la base pausada y
        # despausar antes de que corra el segundo intento.
        await asyncio.sleep(1.2)
        contenedor_docker.unpause()
        pausado = False
        await tarea
        duracion = time.monotonic() - inicio
    finally:
        if pausado:
            contenedor_docker.unpause()
        await worker.close()

    assert duracion < _LIMITE_S, f"tardó {duracion:.2f}s"

    engine_verificacion = crear_engine(configuracion_test)
    try:
        with engine_verificacion.connect() as conexion:
            fila = conexion.execute(
                text("SELECT request_id FROM trabajos_hechos WHERE clave = :clave"),
                {"clave": clave},
            ).first()
    finally:
        engine_verificacion.dispose()
    assert fila is not None
    assert str(fila[0]) == request_id
