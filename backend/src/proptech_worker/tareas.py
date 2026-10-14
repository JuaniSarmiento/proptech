"""Tareas registradas en el worker (D3). Cambio 1c, tarea 5.4.

Escenarios de `cola-de-trabajos`: Tarea de prueba exitosa; Cantidad de fallas
fuera de rango; Sin ruta pública para la tarea de prueba.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from proptech_core.compartido.cola import ResultadoEncolado
from proptech_core.compartido.idempotencia import ejecutar_una_vez
from proptech_core.compartido.reintentos import ErrorPasajero, reintentable
from proptech_core.compartido.seguimiento import con_seguimiento_de_tarea

#: Nombre de la tarea tal como queda registrada en ARQ y en `trabajos_hechos`.
NOMBRE_TAREA_DE_PRUEBA = "tarea_de_prueba"

#: Cota propia de la operación de base que corre en el hilo (D18, F2b vuelta
#: 3): mismo patrón que `PLAZO_VERIFICACION_S` de `proptech_api.salud`. Nace
#: **adentro** de `reintentable` (el decorador exterior), así un
#: `TimeoutError` (ya pasajero, D3) se reintenta o agota con su evento en vez
#: de que ARQ dé el trabajo por fallado desde afuera cuando vence
#: `job_timeout`. Tiene que ser menor que cualquier `job_timeout` configurado
#: (120 s en producción, D2) con margen; una operación sana (un INSERT) tarda
#: milisegundos.
#:
#: **LIMITACIÓN CONOCIDA (F2c, vuelta 3 del auditor)**: `asyncio.wait_for`
#: corta la ESPERA del event loop, no el hilo: no hay forma de matar un hilo
#: de Python desde afuera. Si la base queda congelada más tiempo que TODOS
#: los reintentos (`intentos_maximos` de `PoliticaReintentos`), ARQ ya marcó
#: el trabajo `tarea_agotada` cuando el hilo del PRIMER intento, que sigue
#: corriendo en segundo plano, puede confirmar igual: `ejecutar_una_vez`
#: deja la fila en `trabajos_hechos` para un trabajo que el log ya dio por
#: agotado. Acá no importa porque el efecto es vacío (`lambda _sesion:
#: None`): la fila es sólo evidencia de que el intento corrió, no un efecto
#: real que alguien más dependa de que haya pasado o no.
#:
#: **Este patrón NO se copia para una tarea con efecto real** (mandar un
#: email, mover plata, confirmar una reserva): ahí una confirmación tardía
#: después de `tarea_agotada` es un efecto que nadie esperaba y que nadie va
#: a reintentar ni a revisar. El cambio 7 (la primera tarea con efecto real)
#: tiene que resolver esto del lado de la BASE antes de registrar esa tarea:
#: `statement_timeout`/`lock_timeout` de PostgreSQL (o el `connect_args` de
#: libpq que corresponda) para que la sentencia se corte sola del lado del
#: servidor, más una cota propia POR TAREA (no una constante genérica como
#: ésta) acorde al efecto que hace. No alcanza con acotar la espera del lado
#: del cliente: el hilo tiene que dejar de existir, o la sentencia tiene que
#: morir en el servidor, antes de confirmar nada.
COTA_OPERACION_S = 1.5


class Cola(Protocol):
    """El puerto `Cola` (D4), visto desde quien encola (duck typing)."""

    async def encolar(
        self, tarea: str, *, clave: str, request_id: str, **datos: Any
    ) -> ResultadoEncolado: ...


class ArgumentoDeTareaInvalido(ValueError):
    """Un argumento de una tarea no pasa su modelo de validación (D3): el
    mensaje nombra el campo, nunca el valor recibido."""


class _ArgumentosTareaDePrueba(BaseModel):
    """`fallar_veces` es un entero estricto entre 0 y 10 (D3): en modo
    estricto, pydantic rechaza booleanos, texto y números con decimales en
    vez de convertirlos (L-008: coincidencia completa de tipo, no sólo de
    valor)."""

    model_config = ConfigDict(strict=True)

    fallar_veces: int = Field(ge=0, le=10)


def _validar_fallar_veces(fallar_veces: Any) -> int:
    try:
        return _ArgumentosTareaDePrueba(fallar_veces=fallar_veces).fallar_veces
    except ValidationError as error:
        raise ArgumentoDeTareaInvalido(f"fallar_veces: {error.errors()[0]['msg']}") from None


async def encolar_tarea_de_prueba(
    cola: Cola, *, clave: str, request_id: str, fallar_veces: Any
) -> ResultadoEncolado:
    """Valida `fallar_veces` (D3) antes de tocar la cola: 0 a 10, entero
    estricto. Un valor inválido no encola nada."""
    validado = _validar_fallar_veces(fallar_veces)
    return await cola.encolar(
        NOMBRE_TAREA_DE_PRUEBA, clave=clave, request_id=request_id, fallar_veces=validado
    )


def _registrar_en_un_hilo(fabrica: Any, *, clave: str, request_id: str) -> bool:
    """El trabajo de base de la tarea (D2): se corre con `asyncio.to_thread`
    desde `tarea_de_prueba`, nunca directo en el event loop. Una sesión
    síncrona de SQLAlchemy puede colgarse (`pool_pre_ping` contra una
    conexión del pool cuya base se congeló, L-001) y, si eso pasara en el
    propio event loop, frenaría TODO el worker: ni `job_timeout` ni el
    health check de ARQ podrían correr mientras tanto."""
    with fabrica() as sesion:
        return ejecutar_una_vez(
            sesion,
            clave=clave,
            tarea=NOMBRE_TAREA_DE_PRUEBA,
            request_id=request_id,
            efecto=lambda _sesion: None,
        )


@con_seguimiento_de_tarea
@reintentable
async def tarea_de_prueba(
    ctx: dict[str, Any], *, request_id: str, clave: str, fallar_veces: Any, **datos: Any
) -> bool:
    """La tarea registrada en el worker (D3): valida otra vez `fallar_veces`
    al ejecutar (la cola pudo recibir un trabajo armado a mano), simula
    `fallar_veces` fallas pasajeras y, al completar, registra `clave` en
    `trabajos_hechos` con un efecto vacío (la fila es el efecto observable).

    `**datos` (D2, contrato de toda tarea): acepta y descarta cualquier
    argumento extra sin fallar (la tarea 5.7 encola uno marcado para probar
    que ARQ no lo deja en los logs)."""
    validado = _validar_fallar_veces(fallar_veces)
    if ctx["job_try"] <= validado:
        raise ErrorPasajero("fallo simulado de la tarea de prueba")
    fabrica = ctx["fabrica_de_sesiones"]
    # `asyncio.to_thread` copia el `contextvars.Context` actual al hilo (D2):
    # así el `request_id` que fijó `con_seguimiento_de_tarea` en la
    # `ContextVar` llega al evento `after_begin` de la sesión, que corre
    # dentro de ese mismo hilo. `asyncio.wait_for` acota la ESPERA del event
    # loop (D18, F2b): si la base está congelada, acá adentro ya se levanta
    # `TimeoutError` (pasajero por naturaleza, D3) antes de que `job_timeout`
    # venza afuera de `reintentable`.
    #
    # LIMITACIÓN CONOCIDA (F2c, ver el comentario de `COTA_OPERACION_S`):
    # esto corta la espera, NUNCA el hilo. El hilo sigue corriendo colgado
    # en segundo plano y, si la base vuelve después de agotados todos los
    # reintentos, puede confirmar su `INSERT` con el trabajo ya marcado
    # `tarea_agotada`. Tolerable acá porque el efecto es vacío; el cambio 7
    # no puede heredar este patrón para una tarea con efecto real sin
    # resolverlo primero con un corte del lado de la base.
    return await asyncio.wait_for(
        asyncio.to_thread(_registrar_en_un_hilo, fabrica, clave=clave, request_id=request_id),
        timeout=COTA_OPERACION_S,
    )
