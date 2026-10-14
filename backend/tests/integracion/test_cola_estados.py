"""Los tres estados de Redis sobre el adaptador de la cola (D1, D4, L-001).
Cambio 1c, tarea 4.5.

Contenedor propio del test en cada caso (nunca el de sesión de `conftest.py`
ni el de Compose, L-006); el pausado se despausa siempre en un `finally`.

Escenarios de `cola-de-trabajos`: Redis caído; Redis congelado; Redis lento.
Lecciones: L-001, L-006, L-007.
"""

import asyncio
import contextlib
import time
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import redis.asyncio as redis_asincronico
from arq.connections import RedisSettings
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from proptech_core.compartido.cola import AdaptadorColaArq, ColaNoDisponible, ResultadoEncolado

pytestmark = pytest.mark.integracion

#: Contraseña sólo de este contenedor de test (nunca una credencial real).
_PASSWORD = "prueba-cola-estados-no-real"
_LIMITE_S = 3.0


@pytest.fixture
def contenedor_propio() -> Iterator[DockerContainer]:
    from ..conftest import IMAGEN_REDIS_PARA_TESTS

    contenedor = (
        DockerContainer(IMAGEN_REDIS_PARA_TESTS)
        .with_command(f"redis-server --requirepass {_PASSWORD} --enable-debug-command yes")
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    with contenedor as iniciado:
        yield iniciado


def _ajustes(contenedor: DockerContainer) -> RedisSettings:
    return RedisSettings(
        host=contenedor.get_container_host_ip(),
        port=int(contenedor.get_exposed_port(6379)),
        password=_PASSWORD,
        conn_timeout=2,
        conn_retries=0,
    )


@pytest.fixture
async def cliente_crudo(
    contenedor_propio: DockerContainer,
) -> AsyncIterator[redis_asincronico.Redis]:
    cliente = redis_asincronico.Redis(
        host=contenedor_propio.get_container_host_ip(),
        port=int(contenedor_propio.get_exposed_port(6379)),
        password=_PASSWORD,
    )
    try:
        yield cliente
    finally:
        await cliente.aclose()


@pytest.mark.anyio
async def test_redis_caido_da_cola_no_disponible_en_menos_de_3s(
    contenedor_propio: DockerContainer,
) -> None:
    adaptador = AdaptadorColaArq(_ajustes(contenedor_propio))
    contenedor_propio.get_wrapped_container().stop()

    inicio = time.monotonic()
    with pytest.raises(ColaNoDisponible):
        await adaptador.encolar(
            "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
        )
    duracion = time.monotonic() - inicio
    assert duracion < _LIMITE_S, f"tardó {duracion:.2f}s"


@pytest.mark.anyio
async def test_redis_congelado_da_cola_no_disponible_en_menos_de_3s_y_se_recupera(
    contenedor_propio: DockerContainer,
) -> None:
    adaptador = AdaptadorColaArq(_ajustes(contenedor_propio))
    # Primero una conexión sana: el pool queda creado y abierto (gemelo del
    # patrón de `test_salud_base_congelada.py` para PostgreSQL).
    primero = await adaptador.encolar(
        "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
    )
    assert primero is ResultadoEncolado.ENCOLADO

    contenedor_docker = contenedor_propio.get_wrapped_container()
    contenedor_docker.pause()
    try:
        inicio = time.monotonic()
        with pytest.raises(ColaNoDisponible):
            await adaptador.encolar(
                "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
            )
        duracion = time.monotonic() - inicio
        assert duracion < _LIMITE_S, f"tardó {duracion:.2f}s"
    finally:
        contenedor_docker.unpause()

    # Despausado: el siguiente encolado funciona (el pool se recreó).
    tercero = await adaptador.encolar(
        "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
    )
    assert tercero is ResultadoEncolado.ENCOLADO


@pytest.mark.anyio
async def test_debug_sleep_por_encima_del_limite_da_cola_no_disponible_en_menos_de_3s(
    contenedor_propio: DockerContainer,
    cliente_crudo: redis_asincronico.Redis,
) -> None:
    adaptador = AdaptadorColaArq(_ajustes(contenedor_propio))
    tarea_bloqueo = asyncio.create_task(
        cliente_crudo.execute_command("DEBUG", "SLEEP", "4")  # type: ignore[no-untyped-call]
    )
    await asyncio.sleep(0.5)  # darle tiempo a que el SLEEP tome el servidor de verdad

    inicio = time.monotonic()
    with pytest.raises(ColaNoDisponible):
        await adaptador.encolar(
            "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
        )
    duracion = time.monotonic() - inicio
    assert duracion < _LIMITE_S, f"tardó {duracion:.2f}s"

    tarea_bloqueo.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await tarea_bloqueo


@pytest.mark.anyio
async def test_debug_sleep_por_debajo_del_limite_encola(
    contenedor_propio: DockerContainer,
    cliente_crudo: redis_asincronico.Redis,
) -> None:
    adaptador = AdaptadorColaArq(_ajustes(contenedor_propio))
    tarea_bloqueo = asyncio.create_task(
        cliente_crudo.execute_command("DEBUG", "SLEEP", "0.2")  # type: ignore[no-untyped-call]
    )
    await asyncio.sleep(0.05)

    resultado = await adaptador.encolar(
        "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
    )
    assert resultado is ResultadoEncolado.ENCOLADO

    await tarea_bloqueo


@pytest.mark.anyio
async def test_mensaje_y_logs_no_contienen_host_ni_puerto_ni_error_de_redis_py(
    contenedor_propio: DockerContainer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    ajustes = _ajustes(contenedor_propio)
    host = ajustes.host
    puerto = ajustes.port
    adaptador = AdaptadorColaArq(ajustes)
    contenedor_propio.get_wrapped_container().stop()

    with pytest.raises(ColaNoDisponible) as exc_info:
        await adaptador.encolar(
            "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
        )

    salida = capsys.readouterr()
    for fragmento in (str(host), str(puerto), "Connection refused", "Error 111"):
        assert fragmento not in str(exc_info.value)
        assert fragmento not in salida.out
        assert fragmento not in salida.err
