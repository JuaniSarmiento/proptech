"""Ataque del rompedor (vuelta 2, F8; D3 capa 1, D4): `encolar` no valida
`clave` ni los nombres de `**datos`. ARQ trata `_job_id=""` como "sin id" y
genera uno al azar (se pierde la deduplicación), y cualquier
`_queue_name`/`_defer_by`/`_expires`/`_job_try` en `datos` le llega a
`enqueue_job` como opción propia en vez de argumento del trabajo.
"""

import uuid
from typing import Any

import pytest
from arq.connections import RedisSettings
from testcontainers.core.container import DockerContainer

from proptech_core.compartido.cola import AdaptadorColaArq, ResultadoEncolado

from ..conftest import REDIS_PASSWORD_DE_PRUEBA

pytestmark = [pytest.mark.integracion, pytest.mark.anyio]

_RID = "3f2c1a00-0001-4001-8001-000000000001"


def _cola(redis_contenedor: DockerContainer) -> AdaptadorColaArq:
    return AdaptadorColaArq(
        RedisSettings(
            host=redis_contenedor.get_container_host_ip(),
            port=int(redis_contenedor.get_exposed_port(6379)),
            password=REDIS_PASSWORD_DE_PRUEBA,
        )
    )


async def test_clave_vacia_se_rechaza_o_no_duplica(redis_contenedor: DockerContainer) -> None:
    cola = _cola(redis_contenedor)
    try:
        primero = await cola.encolar("tarea_de_prueba", clave="", request_id=_RID, fallar_veces=0)
        segundo = await cola.encolar("tarea_de_prueba", clave="", request_id=_RID, fallar_veces=0)
    except ValueError:
        return  # rechazarla antes de tocar Redis también cumple
    assert (primero, segundo) != (ResultadoEncolado.ENCOLADO, ResultadoEncolado.ENCOLADO)


@pytest.mark.parametrize("opcion", ["_queue_name", "_defer_by", "_expires", "_job_try"])
async def test_un_dato_con_nombre_de_opcion_de_arq_se_rechaza(
    redis_contenedor: DockerContainer, opcion: str
) -> None:
    cola = _cola(redis_contenedor)
    extra: dict[str, Any] = {opcion: "arq:queue:nadie" if opcion == "_queue_name" else 1}
    with pytest.raises(ValueError):
        await cola.encolar(
            "tarea_de_prueba",
            clave=f"opcion-{uuid.uuid4()}",
            request_id=_RID,
            fallar_veces=0,
            **extra,
        )
