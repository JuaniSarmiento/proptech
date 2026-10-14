"""Conexión a Redis, en un solo módulo (D4, D18).

Único lugar, junto con `configuracion.py` (`url_sqlalchemy`, para PostgreSQL),
con permiso de leer el valor real de una contraseña con `get_secret_value()`.
De acá toman su conexión el adaptador de la cola (`cola.py`), el verificador
de cola de `/api/salud` (tarea 4.6) y los `RedisSettings` del worker (tarea
5.5): el test `test_get_secret_value_solo_aparece_en_configuracion_o_conexion_redis`
(3.5) exige que `get_secret_value` no aparezca en ningún otro archivo.
"""

from __future__ import annotations

import redis
from arq.connections import RedisSettings

from proptech_core.compartido.configuracion import Configuracion


def cliente_redis_sincrono(configuracion: Configuracion, *, timeout: int = 2) -> redis.Redis:
    """Cliente síncrono de redis-py para el verificador de cola de
    `/api/salud` (D4, tarea 4.6): `socket_connect_timeout` y `socket_timeout`
    acotan tanto la conexión como el `PING`."""
    return redis.Redis(
        host=configuracion.redis_host,
        port=configuracion.redis_port,
        password=configuracion.redis_password.get_secret_value(),
        socket_connect_timeout=timeout,
        socket_timeout=timeout,
    )


def ajustes_redis_arq(
    configuracion: Configuracion, *, conn_timeout: int = 2, conn_retries: int = 0
) -> RedisSettings:
    """`RedisSettings` de ARQ a partir de la configuración (D4).

    `conn_retries` difiere entre procesos: la API falla rápido (`0`, D4); el
    worker reintenta más (`5`, tarea 5.5), porque un reinicio de Redis no
    tiene por qué tirar abajo los trabajos ya tomados.
    """
    return RedisSettings(
        host=configuracion.redis_host,
        port=configuracion.redis_port,
        password=configuracion.redis_password.get_secret_value(),
        conn_timeout=conn_timeout,
        conn_retries=conn_retries,
    )
