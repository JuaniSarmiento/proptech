"""Adaptador de la cola contra Redis real (D2, D4). Cambio 1c, tarea 4.4.

Escenarios de `cola-de-trabajos`: Mismo trabajo encolado dos veces; Trabajo
encolado inspeccionado en Redis; Monto como número al encolar. Lecciones:
L-007.
"""

import json
import uuid

import pytest
import redis.asyncio as redis_asincronico
from testcontainers.core.container import DockerContainer

from proptech_core.compartido.cola import AdaptadorColaArq, ArgumentoNoPermitido, ResultadoEncolado
from proptech_core.compartido.conexion_redis import ajustes_redis_arq
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.dinero import Dinero

pytestmark = pytest.mark.integracion

MARCADOR_ERROR_REDIS = "marcador-error-redis-9c4a1f"


def _configuracion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, contenedor: DockerContainer
) -> Configuracion:
    ruta = tmp_path / "parametros.yaml"  # type: ignore[operator]
    ruta.write_text("version: 1\n")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    # Nunca se conecta de verdad (sólo Redis importa en este archivo): el
    # valor sólo tiene que cumplir el patrón proptech_* del rol de la app (D3).
    monkeypatch.setenv("POSTGRES_APP_USER", "proptech_x")
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", "x")
    monkeypatch.setenv("POSTGRES_DB", "x")
    monkeypatch.setenv("REDIS_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("REDIS_PORT", str(contenedor.get_exposed_port(6379)))
    from tests.conftest import REDIS_PASSWORD_DE_PRUEBA

    monkeypatch.setenv("REDIS_PASSWORD", REDIS_PASSWORD_DE_PRUEBA)
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta))
    return Configuracion()


def _adaptador(configuracion: Configuracion) -> AdaptadorColaArq:
    return AdaptadorColaArq(ajustes_redis_arq(configuracion))


@pytest.mark.anyio
async def test_encolar_devuelve_encolado(
    redis_contenedor: DockerContainer, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    configuracion = _configuracion(monkeypatch, tmp_path, redis_contenedor)
    adaptador = _adaptador(configuracion)
    resultado = await adaptador.encolar(
        "tarea_de_prueba",
        clave=f"prueba-{uuid.uuid4()}",
        request_id=str(uuid.uuid4()),
        fallar_veces=0,
    )
    assert resultado is ResultadoEncolado.ENCOLADO


@pytest.mark.anyio
async def test_la_misma_clave_dos_veces_devuelve_ya_encolado(
    redis_contenedor: DockerContainer, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    configuracion = _configuracion(monkeypatch, tmp_path, redis_contenedor)
    adaptador = _adaptador(configuracion)
    clave = f"prueba-{uuid.uuid4()}"
    primero = await adaptador.encolar(
        "tarea_de_prueba", clave=clave, request_id=str(uuid.uuid4()), fallar_veces=0
    )
    segundo = await adaptador.encolar(
        "tarea_de_prueba", clave=clave, request_id=str(uuid.uuid4()), fallar_veces=0
    )
    assert primero is ResultadoEncolado.ENCOLADO
    assert segundo is ResultadoEncolado.YA_ENCOLADO


@pytest.mark.anyio
async def test_el_trabajo_crudo_en_redis_es_json_con_los_argumentos_por_nombre(
    redis_contenedor: DockerContainer, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    configuracion = _configuracion(monkeypatch, tmp_path, redis_contenedor)
    adaptador = _adaptador(configuracion)
    clave = f"prueba-{uuid.uuid4()}"
    request_id = str(uuid.uuid4())
    await adaptador.encolar("tarea_de_prueba", clave=clave, request_id=request_id, fallar_veces=3)

    cliente = redis_asincronico.Redis(
        host=configuracion.redis_host,
        port=configuracion.redis_port,
        password=configuracion.redis_password.get_secret_value(),
    )
    try:
        crudo = await cliente.get(f"arq:job:{clave}")
        assert crudo is not None
        datos = json.loads(crudo)
        assert datos["k"]["clave"] == clave
        assert datos["k"]["request_id"] == request_id
        assert datos["k"]["fallar_veces"] == 3
    finally:
        await cliente.aclose()


@pytest.mark.parametrize(
    ("datos", "fragmento_esperado"),
    [
        ({"monto": 20000.0}, "monto"),
        ({"monto": 20000.5}, "monto"),
        ({"montos": ["1.00", 2.5]}, "montos[1]"),
        ({"detalle": {"total": 10.5}}, "detalle.total"),
        ({"monto": Dinero("10.00")}, "monto"),
    ],
)
@pytest.mark.anyio
async def test_argumento_float_o_decimal_se_rechaza_antes_de_tocar_redis(
    redis_contenedor: DockerContainer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
    datos: dict[str, object],
    fragmento_esperado: str,
) -> None:
    configuracion = _configuracion(monkeypatch, tmp_path, redis_contenedor)
    adaptador = _adaptador(configuracion)
    clave = f"prueba-{uuid.uuid4()}"
    with pytest.raises(ArgumentoNoPermitido) as exc_info:
        await adaptador.encolar(
            "tarea_de_prueba", clave=clave, request_id=str(uuid.uuid4()), **datos
        )
    assert fragmento_esperado in str(exc_info.value)
    assert "20000" not in str(exc_info.value)
    assert "10.5" not in str(exc_info.value)
    assert "10.00" not in str(exc_info.value)

    cliente = redis_asincronico.Redis(
        host=configuracion.redis_host,
        port=configuracion.redis_port,
        password=configuracion.redis_password.get_secret_value(),
    )
    try:
        assert await cliente.get(f"arq:job:{clave}") is None
    finally:
        await cliente.aclose()


@pytest.mark.anyio
async def test_connection_error_real_con_marcador_no_aparece_en_la_salida(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Redis caído (no el contenedor de sesión, L-006): un `ConnectionError`
    real de redis-py pasado por `configurar_logs` no deja el marcador del
    error en la salida (D13, L-007; caso de redis-py que no entra en 2.2)."""
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")

    contenedor_caido = DockerContainer("redis:8.10.2-trixie").with_exposed_ports(6379)
    contenedor_caido.start()
    try:
        host = contenedor_caido.get_container_host_ip()
        puerto = int(contenedor_caido.get_exposed_port(6379))
    finally:
        # .stop() de testcontainers detiene Y elimina el contenedor (una sola
        # vez: no hay `with` acá, así no se intenta un segundo stop/remove).
        contenedor_caido.stop()

    from arq.connections import RedisSettings

    from proptech_core.compartido.cola import AdaptadorColaArq, ColaNoDisponible

    ajustes = RedisSettings(
        host=host, port=puerto, password=MARCADOR_ERROR_REDIS, conn_timeout=1, conn_retries=0
    )
    adaptador = AdaptadorColaArq(ajustes)

    with pytest.raises(ColaNoDisponible) as exc_info:
        await adaptador.encolar(
            "tarea_de_prueba", clave=str(uuid.uuid4()), request_id=str(uuid.uuid4())
        )

    salida = capsys.readouterr()
    assert MARCADOR_ERROR_REDIS not in str(exc_info.value)
    assert MARCADOR_ERROR_REDIS not in salida.out
    assert MARCADOR_ERROR_REDIS not in salida.err
