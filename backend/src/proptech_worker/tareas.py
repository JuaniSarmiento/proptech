"""Tareas registradas en el worker (D3). Cambio 1c, tarea 5.4.

Escenarios de `cola-de-trabajos`: Tarea de prueba exitosa; Cantidad de fallas
fuera de rango; Sin ruta pública para la tarea de prueba.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text

from proptech_core.acceso.adaptadores.clerk_http import ClerkNoDisponible, ClerkRechazoDefinitivo
from proptech_core.acceso.puertos import ClienteDeClerk
from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.cola import ResultadoEncolado
from proptech_core.compartido.idempotencia import ejecutar_una_vez
from proptech_core.compartido.reintentos import ErrorPasajero, reintentable
from proptech_core.compartido.seguimiento import con_seguimiento_de_tarea

_logger_invitaciones = logging.getLogger("proptech_worker.tareas.invitaciones")

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


# --- 2b, tarea 5.4: el worker habla con Clerk (D7) ------------------------
#
# `enviar_invitacion` y `revocar_invitacion_en_clerk` son las primeras
# tareas con un efecto real (D7, nota de `COTA_OPERACION_S` arriba): la
# idempotencia no es la de `ejecutar_una_vez` (una clave en
# `trabajos_hechos`), sino la del propio estado de `invitacion` (D3, D7):
# sólo se llama a Clerk si la fila sigue `pendiente`, y el `UPDATE` que la
# mueve de estado exige ese mismo `pendiente` en el `WHERE`, así que un
# trabajo repetido después de que la fila ya cambió no vuelve a llamar al
# servidor ni a pisar un estado posterior.


def _uuid_desde_texto(valor: Any) -> Any:
    """Los dos ids llegan como texto (D2: la cola nunca transporta tipos
    propios, cola.py). En modo estricto pydantic rechaza convertir un texto
    a `UUID` (exige una instancia ya hecha); este validador lo intenta
    ANTES de esa comprobación: si no es texto, lo deja pasar tal cual (un
    `int` o un `bool` siguen rechazados por el chequeo estricto de tipo,
    nunca por éste), y si es texto mal formado, `UUID()` levanta su propio
    `ValueError`, que pydantic envuelve nombrando el campo."""
    return UUID(valor) if isinstance(valor, str) else valor


class _ArgumentosEnviarInvitacion(BaseModel):
    model_config = ConfigDict(strict=True)

    administracion_id: UUID
    invitacion_id: UUID
    sobre: str = Field(min_length=1)

    _ids_desde_texto = field_validator("administracion_id", "invitacion_id", mode="before")(
        _uuid_desde_texto
    )


class _ArgumentosRevocarInvitacion(BaseModel):
    model_config = ConfigDict(strict=True)

    administracion_id: UUID
    invitacion_id: UUID

    _ids_desde_texto = field_validator("administracion_id", "invitacion_id", mode="before")(
        _uuid_desde_texto
    )


def _leer_invitacion_para_enviar(
    fabrica: Any, *, administracion_id: UUID, invitacion_id: UUID
) -> str | None:
    """El email de la persona si la invitación sigue `pendiente` bajo el
    tenant (D7, 2a); `None` si no existe (id ajeno o de otra administración,
    RLS da cero filas) o si ya no está `pendiente` (ya enviada, revocada o
    repetida)."""
    with abrir_sesion(fabrica, administracion_id) as sesion:
        fila = sesion.execute(
            text(
                "SELECT i.estado, p.email FROM invitacion i "
                "JOIN persona p ON p.administracion_id = i.administracion_id "
                "AND p.id = i.persona_id "
                "WHERE i.id = :invitacion AND i.administracion_id = :admin"
            ),
            {"invitacion": str(invitacion_id), "admin": str(administracion_id)},
        ).first()
        sesion.rollback()
    if fila is None or fila.estado != "pendiente":
        return None
    email: str = fila.email
    return email


def _marcar_invitacion_enviada_o_fallida(
    fabrica: Any,
    *,
    administracion_id: UUID,
    invitacion_id: UUID,
    estado: str,
    clerk_invitacion_id: str | None,
) -> str | None:
    """Guarda el `clerk_invitacion_id` SIEMPRE que la fila siga existiendo
    bajo el tenant (R2B-1): si sólo se guardara cuando la fila está
    `pendiente`, una revocación que gana la carrera (la deja `revocada`
    antes de que Clerk conteste) hace perder el id para siempre, y
    `revocar_invitacion_en_clerk` nunca encuentra qué revocar. El `estado`
    en cambio sólo se pisa si la fila TODAVÍA está `pendiente`: un trabajo
    repetido, o uno que llegó tarde después de una revocación, nunca
    retrocede un estado final (`revocada`/`fallida`) que ya haya quedado
    escrito. Devuelve el estado final de la fila (`None` si ya no existe),
    para que `enviar_invitacion` sepa si tiene que revocar ella misma."""
    with abrir_sesion(fabrica, administracion_id) as sesion:
        fila = sesion.execute(
            text(
                "UPDATE invitacion SET "
                "clerk_invitacion_id = COALESCE(:clerk_id, clerk_invitacion_id), "
                "estado = CASE WHEN estado = 'pendiente' THEN :estado ELSE estado END "
                "WHERE id=:invitacion AND administracion_id=:admin "
                "RETURNING estado"
            ),
            {
                "estado": estado,
                "clerk_id": clerk_invitacion_id,
                "invitacion": str(invitacion_id),
                "admin": str(administracion_id),
            },
        ).first()
        sesion.commit()
    return fila.estado if fila is not None else None


@con_seguimiento_de_tarea
@reintentable
async def enviar_invitacion(
    ctx: dict[str, Any],
    *,
    request_id: str,
    clave: str,
    administracion_id: Any,
    invitacion_id: Any,
    sobre: Any,
    **datos: Any,
) -> bool:
    """`enviar_invitacion(administracion_id, invitacion_id, sobre)` (D7):
    nunca recibe ni transporta el email ni el token crudo; el email sale de
    la base, bajo el tenant, y el sobre viaja sin abrirse hacia
    `redirect_url`. 4xx (salvo 429) definitivo → `fallida`, sin reintento;
    429, 5xx o sin respuesta → `ErrorPasajero`, reintentable."""
    try:
        argumentos = _ArgumentosEnviarInvitacion(
            administracion_id=administracion_id, invitacion_id=invitacion_id, sobre=sobre
        )
    except ValidationError as error:
        campo = error.errors()[0]["loc"][0]
        raise ArgumentoDeTareaInvalido(f"enviar_invitacion: {campo}") from None

    fabrica = ctx["fabrica_de_sesiones"]
    email = await asyncio.to_thread(
        _leer_invitacion_para_enviar,
        fabrica,
        administracion_id=argumentos.administracion_id,
        invitacion_id=argumentos.invitacion_id,
    )
    if email is None:
        _logger_invitaciones.info("invitacion_no_pendiente", extra={"tarea": "enviar_invitacion"})
        return True

    clerk: ClienteDeClerk | None = ctx["clerk"]
    if clerk is None:
        # Sin CLERK_SECRET_KEY (D7, hoy en blanco en `.env.example`): apaga
        # el envío, nunca al worker entero (mismo criterio que D1 con
        # CLERK_JWT_KEY). Reintenta como si Clerk no respondiera.
        raise ErrorPasajero("CLERK_SECRET_KEY no configurada")
    configuracion = ctx["configuracion_app"]
    dias = ctx["parametros"].invitaciones.vencimiento_dias
    redirect_url = f"{configuracion.proptech_url_publica}/invitacion/{sobre}"
    try:
        clerk_invitacion_id = await clerk.invitar(
            email=email, redirect_url=redirect_url, expires_in_days=dias
        )
    except ClerkRechazoDefinitivo:
        await asyncio.to_thread(
            _marcar_invitacion_enviada_o_fallida,
            fabrica,
            administracion_id=argumentos.administracion_id,
            invitacion_id=argumentos.invitacion_id,
            estado="fallida",
            clerk_invitacion_id=None,
        )
        return False
    except ClerkNoDisponible as error:
        raise ErrorPasajero("clerk no disponible") from error

    estado_final = await asyncio.to_thread(
        _marcar_invitacion_enviada_o_fallida,
        fabrica,
        administracion_id=argumentos.administracion_id,
        invitacion_id=argumentos.invitacion_id,
        estado="enviada",
        clerk_invitacion_id=clerk_invitacion_id,
    )
    if estado_final == "revocada":
        # R2B-1: la revocaron (o la reinvitaron) mientras este POST estaba
        # en vuelo. El id recién quedó guardado más arriba; el trabajo de
        # revocación que encoló ese pedido pudo haber corrido ANTES y no
        # haber encontrado nada, así que la invitación de Clerk nunca
        # queda abierta: la revocamos nosotros mismos, en el mismo
        # trabajo, en vez de depender de un trabajo ya terminado.
        try:
            await clerk.revocar(clerk_invitacion_id)
        except ClerkRechazoDefinitivo:
            pass
        except ClerkNoDisponible as error:
            raise ErrorPasajero("clerk no disponible") from error
    return True


def _leer_clerk_id_para_revocar(
    fabrica: Any, *, administracion_id: UUID, invitacion_id: UUID
) -> str | None:
    """El `clerk_invitacion_id` de la fila bajo el tenant (D7, 2a); `None`
    si la fila no existe (id ajeno) o si nunca se llegó a enviar (no hay
    nada que revocar en Clerk: el estado ya quedó `revocada` en la base por
    la misma transacción que generó este trabajo)."""
    with abrir_sesion(fabrica, administracion_id) as sesion:
        fila = sesion.execute(
            text(
                "SELECT clerk_invitacion_id FROM invitacion "
                "WHERE id=:invitacion AND administracion_id=:admin"
            ),
            {"invitacion": str(invitacion_id), "admin": str(administracion_id)},
        ).first()
        sesion.rollback()
    if fila is None:
        return None
    clerk_id: str | None = fila.clerk_invitacion_id
    return clerk_id


@con_seguimiento_de_tarea
@reintentable
async def revocar_invitacion_en_clerk(
    ctx: dict[str, Any],
    *,
    request_id: str,
    clave: str,
    administracion_id: Any,
    invitacion_id: Any,
    **datos: Any,
) -> bool:
    """`revocar_invitacion_en_clerk(administracion_id, invitacion_id)` (D7):
    la fila ya quedó `revocada` en la base (5.2, misma transacción que la
    reinvitación); esta tarea sólo avisa a Clerk si llegó a enviarse."""
    try:
        argumentos = _ArgumentosRevocarInvitacion(
            administracion_id=administracion_id, invitacion_id=invitacion_id
        )
    except ValidationError as error:
        raise ArgumentoDeTareaInvalido(
            f"revocar_invitacion_en_clerk: {error.errors()[0]['loc'][0]}"
        ) from None

    fabrica = ctx["fabrica_de_sesiones"]
    clerk_invitacion_id = await asyncio.to_thread(
        _leer_clerk_id_para_revocar,
        fabrica,
        administracion_id=argumentos.administracion_id,
        invitacion_id=argumentos.invitacion_id,
    )
    if clerk_invitacion_id is None:
        return True

    clerk: ClienteDeClerk | None = ctx["clerk"]
    if clerk is None:
        raise ErrorPasajero("CLERK_SECRET_KEY no configurada")
    try:
        await clerk.revocar(clerk_invitacion_id)
    except ClerkRechazoDefinitivo:
        return False
    except ClerkNoDisponible as error:
        raise ErrorPasajero("clerk no disponible") from error
    return True
