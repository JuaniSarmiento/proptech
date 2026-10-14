"""Test del comando `python -m proptech_worker.prueba encolar` contra Redis
real (D3). Cambio 1c, tarea 5.11.

Escenarios de `cola-de-trabajos`: Tarea de prueba exitosa (forma de
encolarla que usa el humo del 1d); Cantidad de fallas fuera de rango.
"""

import os
import subprocess
import sys
from typing import Any

import pytest
import redis.asyncio as redis_asincronico

pytestmark = pytest.mark.integracion


def _parsear_salida(stdout: str) -> dict[str, str]:
    datos = {}
    for linea in stdout.strip().splitlines():
        clave, _, valor = linea.partition("=")
        datos[clave.strip()] = valor.strip()
    return datos


def _entorno_hacia_el_contenedor_real(ajustes_del_worker: Any) -> dict[str, str]:
    """`tests/integracion/conftest.py` pisa `REDIS_HOST/PORT/PASSWORD` con
    valores de ejemplo (autouse, para los tests que no les interesa Redis);
    este comando sí necesita llegar al contenedor real de la sesión."""
    ajustes = ajustes_del_worker.AjustesDelWorker.redis_settings
    return {
        **os.environ,
        "REDIS_HOST": str(ajustes.host),
        "REDIS_PORT": str(ajustes.port),
        "REDIS_PASSWORD": str(ajustes.password),
    }


@pytest.mark.anyio
async def test_comando_encolar_imprime_clave_y_request_id_y_queda_en_la_cola(
    ajustes_del_worker: Any,
) -> None:
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_worker.prueba", "encolar", "--fallar-veces", "2"],
        env=_entorno_hacia_el_contenedor_real(ajustes_del_worker),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr

    salida = _parsear_salida(resultado.stdout)
    assert "clave" in salida, resultado.stdout
    assert "request_id" in salida, resultado.stdout

    ajustes = ajustes_del_worker.AjustesDelWorker
    cliente = redis_asincronico.Redis(
        host=ajustes.redis_settings.host,
        port=ajustes.redis_settings.port,
        password=ajustes.redis_settings.password,
    )
    try:
        crudo = await cliente.get(f"arq:job:{salida['clave']}")
        assert crudo is not None, "el trabajo no quedó en la cola"
    finally:
        # Este comando usa la cola default (no una aislada por test: así es
        # como lo usaría el humo real); se limpia a mano para no dejarlo
        # pendiente en el Redis de sesión.
        await cliente.delete(f"arq:job:{salida['clave']}")
        await cliente.zrem("arq:queue", salida["clave"])
        await cliente.aclose()


@pytest.mark.parametrize("fallar_veces", ["-1", "11"])
def test_comando_encolar_con_fallar_veces_fuera_de_rango_termina_nombrando_el_campo(
    ajustes_del_worker: Any, fallar_veces: str
) -> None:
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_worker.prueba", "encolar", "--fallar-veces", fallar_veces],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert resultado.returncode != 0
    assert "fallar_veces" in resultado.stderr, resultado.stderr
