"""Puerto de la cola de trabajos (D2, D4): encolar sin colgarse ante Redis caído.

Los trabajos viajan como JSON, nunca como `pickle` (D2): `encolar` sólo acepta
texto, enteros, booleanos, nulos, listas y mapas con claves de texto. Los
montos van como texto (`Dinero.a_texto()`); cualquier otro tipo (en particular
`float` y `Decimal`, sueltos o anidados) se rechaza antes de tocar Redis con
`ArgumentoNoPermitido`, cuyo mensaje nombra el campo (`monto`, `montos[1]`,
`detalle.total`) sin mostrar su valor (D13, L-007).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

import redis.exceptions
from arq.connections import ArqRedis, RedisSettings, create_pool

from proptech_core.compartido.logs import datos_de_excepcion

_logger = logging.getLogger("proptech_core.compartido.cola")

#: Cota de cada intento de encolado (D4): acota tanto a Redis congelado (el
#: socket existe pero nadie responde) como a Redis lento más allá del límite.
PLAZO_ENCOLADO_S = 2.5


class ResultadoEncolado(StrEnum):
    """Resultado de `Cola.encolar` (D3, D4)."""

    ENCOLADO = "encolado"
    YA_ENCOLADO = "ya_encolado"


class ColaNoDisponible(Exception):
    """La cola no respondió (D4, D13): mensaje propio, nunca el texto del
    error de redis-py ni de ARQ."""


class ArgumentoNoPermitido(ValueError):
    """Un argumento de un trabajo no es de un tipo permitido (D2): el mensaje
    nombra el campo, nunca su valor."""


def serializar_job(datos: dict[str, Any]) -> bytes:
    """Serializador JSON de ARQ (D2): el default de ARQ es `pickle`, que
    ejecutaría código arbitrario si alguien escribe en Redis. El mismo
    serializador lo usa el pool que encola (acá) y el worker (`ajustes.py`,
    tarea 5.5, L-009)."""
    return json.dumps(datos).encode()


def deserializar_job(datos: bytes) -> dict[str, Any]:
    return json.loads(datos)  # type: ignore[no-any-return]


def _validar_argumento(ruta: str, valor: Any) -> None:
    if valor is None or isinstance(valor, bool | int | str):
        return
    if isinstance(valor, list):
        for índice, elemento in enumerate(valor):
            _validar_argumento(f"{ruta}[{índice}]", elemento)
        return
    if isinstance(valor, Mapping):
        for clave, elemento in valor.items():
            if not isinstance(clave, str):
                raise ArgumentoNoPermitido(f"el campo '{ruta}' tiene una clave que no es texto")
            _validar_argumento(f"{ruta}.{clave}", elemento)
        return
    raise ArgumentoNoPermitido(
        f"el campo '{ruta}' tiene un tipo no permitido ({type(valor).__name__}); "
        "los montos van como texto (Dinero.a_texto())"
    )


def validar_datos(datos: Mapping[str, Any]) -> None:
    """Valida los argumentos de un trabajo antes de tocar Redis (D2, D13)."""
    for clave, valor in datos.items():
        _validar_argumento(clave, valor)


#: Mismo largo máximo que el `CHECK (length(clave) BETWEEN 1 AND 200)` de
#: `trabajos_hechos` (migración 0002, D3): una clave más larga encolaría bien
#: y recién fallaría mucho después, al confirmar el efecto en la base.
LARGO_MAXIMO_CLAVE = 200


def _validar_clave(clave: str) -> None:
    """La `clave` de deduplicación (D3 capa 1, vuelta 3 F8b): tiene que ser
    texto, no vacía, no en blanco (sólo espacios o saltos de línea) y no más
    larga que `LARGO_MAXIMO_CLAVE`. ARQ trata `_job_id=""` como "sin id" y
    genera uno al azar, perdiendo la deduplicación en silencio; una clave en
    blanco tiene el mismo problema sin estar vacía para ARQ."""
    if not isinstance(clave, str):
        raise ArgumentoNoPermitido(
            f"el campo 'clave' tiene un tipo no permitido ({type(clave).__name__})"
        )
    if not clave.strip():
        raise ArgumentoNoPermitido("el campo 'clave' no puede estar vacío ni ser sólo espacios")
    if len(clave) > LARGO_MAXIMO_CLAVE:
        raise ArgumentoNoPermitido(
            f"el campo 'clave' no puede superar los {LARGO_MAXIMO_CLAVE} caracteres"
        )


#: Nombre del primer parámetro POSICIONAL de `ArqRedis.enqueue_job` (D2, D4,
#: vuelta 3 F8b): ahí ya va `tarea`, así que un dato llamado `function`
#: choca (`enqueue_job() got multiple values for argument 'function'`, un
#: `TypeError` crudo sin nombrar el campo) en vez de viajar como argumento de
#: la tarea.
_NOMBRE_RESERVADO_POR_ENQUEUE_JOB = "function"


def _validar_nombres_de_datos(datos: Mapping[str, Any]) -> None:
    """Ningún argumento del trabajo puede empezar con `_` (D2, D4): ARQ lee
    `_job_id`, `_queue_name`, `_defer_by`, `_defer_until`, `_expires` y
    `_job_try` de los kwargs de `enqueue_job` como OPCIONES propias de ARQ,
    no como argumentos de la tarea; un dato con uno de esos nombres (o
    cualquier otro que empiece con `_`, por si ARQ suma opciones nuevas)
    cambiaría el comportamiento de la cola en vez de viajar a la tarea.
    Tampoco puede llamarse `function`: choca con el parámetro posicional de
    `enqueue_job` (D13, L-007: error propio que nombra el campo, nunca el
    `TypeError` crudo de Python)."""
    for clave in datos:
        if clave.startswith("_"):
            raise ArgumentoNoPermitido(
                f"el campo '{clave}' no puede empezar con '_' (lo toma ARQ como opción)"
            )
        if clave == _NOMBRE_RESERVADO_POR_ENQUEUE_JOB:
            raise ArgumentoNoPermitido(
                f"el campo '{clave}' no puede usarse (lo toma enqueue_job como su propio parámetro)"
            )


class AdaptadorColaArq:
    """Adaptador del puerto `Cola` sobre ARQ (D2, D4).

    El pool se crea en el primer uso (perezoso) y se descarta ante cualquier
    falla (error de conexión o la cota de `PLAZO_ENCOLADO_S`), para que el
    siguiente intento reconecte en vez de reusar una conexión que ya probó
    estar rota o congelada."""

    def __init__(self, ajustes: RedisSettings) -> None:
        self._ajustes = ajustes
        self._pool: ArqRedis | None = None

    async def _obtener_pool(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(
                self._ajustes,
                job_serializer=serializar_job,
                job_deserializer=deserializar_job,
            )
        return self._pool

    async def encolar(
        self, tarea: str, *, clave: str, request_id: str, **datos: Any
    ) -> ResultadoEncolado:
        _validar_clave(clave)
        _validar_nombres_de_datos(datos)
        validar_datos(datos)
        try:
            # La cota cubre también la creación perezosa del pool: si Redis
            # está congelado o lento, la primera conexión puede colgarse ahí
            # tanto como en el propio `enqueue_job`.
            async with asyncio.timeout(PLAZO_ENCOLADO_S):
                pool = await self._obtener_pool()
                resultado = await pool.enqueue_job(
                    tarea, _job_id=clave, request_id=request_id, clave=clave, **datos
                )
        except (TimeoutError, redis.exceptions.RedisError, OSError) as error:
            # Se descarta el pool: el próximo encolado reconecta en vez de
            # reusar una conexión que ya probó estar rota o congelada.
            self._pool = None
            _logger.error("cola_no_disponible", extra=datos_de_excepcion(error))
            raise ColaNoDisponible("cola no disponible") from None
        return ResultadoEncolado.YA_ENCOLADO if resultado is None else ResultadoEncolado.ENCOLADO
