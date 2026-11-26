"""Tareas registradas en el worker (D3). Cambio 1c, tarea 5.4.

Escenarios de `cola-de-trabajos`: Tarea de prueba exitosa; Cantidad de fallas
fuera de rango; Sin ruta pública para la tarea de prueba.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text

from proptech_core.acceso.adaptadores.clerk_http import ClerkNoDisponible, ClerkRechazoDefinitivo
from proptech_core.acceso.puertos import ClienteDeClerk
from proptech_core.compartido.base_de_datos import abrir_sesion
from proptech_core.compartido.cola import ResultadoEncolado
from proptech_core.compartido.reintentos import ErrorPasajero, reintentable
from proptech_core.compartido.seguimiento import con_seguimiento_de_tarea
from proptech_core.compartido.tenant_de_tarea import con_administracion_de_tarea
from proptech_worker.corte import ejecutar_con_corte

_logger_invitaciones = logging.getLogger("proptech_worker.tareas.invitaciones")

#: Nombre de la tarea tal como queda registrada en ARQ y en `trabajos_hechos`.
NOMBRE_TAREA_DE_PRUEBA = "tarea_de_prueba"

#: Cota propia de `tarea_de_prueba` (D18, F2b vuelta 3; F2c cerrada por H-016, D-158). Cada tarea
#: declara la suya, acorde a su efecto: ya no hay una constante genérica. La cota se aplica del lado
#: de la base (`proptech_worker.corte.ejecutar_con_corte`: `statement_timeout`, `lock_timeout` e
#: `idle_in_transaction_session_timeout` con `SET LOCAL`, más el plazo verificado antes de
#: confirmar),
#: así una sentencia colgada muere en el servidor y una confirmación tardía nunca ocurre: la tarea
#: queda agotada o confirma dentro de su cota, no después. Tiene que ser menor que cualquier
#: `job_timeout` configurado (120 s en producción, D2). Una tarea con efecto real (el PDF de la
#: expensa, el email) declara su cota y pasa por `ejecutar_con_corte`.
COTA_TAREA_DE_PRUEBA_S = 1.5

#: Margen del `asyncio.wait_for` exterior sobre la cota de la tarea: la base corta primero, y el
#: `wait_for` sólo acota la espera del event loop si algo del hilo no responde. Nace adentro de
#: `reintentable` y tiene que vencer antes que el `job_timeout` de ARQ (2 s en los tests, 120 s en
#: producción): si no, ARQ da la tarea por fallada sin pasar por el reintento ni `tarea_agotada`.
MARGEN_DE_ESPERA_S = 0.25


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
    return ejecutar_con_corte(
        fabrica,
        administracion_id=None,
        cota_s=COTA_TAREA_DE_PRUEBA_S,
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
    # `asyncio.to_thread` copia el `contextvars.Context` actual al hilo (D2): así el `request_id`
    # que fijó `con_seguimiento_de_tarea` en la `ContextVar` llega al evento `after_begin` de la
    # sesión, que corre dentro de ese mismo hilo. El corte real es del lado de la base (H-016,
    # F2c): la sentencia muere en el servidor y la transacción no confirma después de
    # `COTA_TAREA_DE_PRUEBA_S`; `asyncio.wait_for` sólo acota la espera del event loop (cota más
    # un margen) y levanta `TimeoutError` (pasajero, D3) si el hilo no responde.
    return await asyncio.wait_for(
        asyncio.to_thread(_registrar_en_un_hilo, fabrica, clave=clave, request_id=request_id),
        timeout=COTA_TAREA_DE_PRUEBA_S + MARGEN_DE_ESPERA_S,
    )


# --- 2b, tarea 5.4: el worker habla con Clerk (D7) ------------------------
#
# `enviar_invitacion` y `revocar_invitacion_en_clerk` son las primeras
# tareas con un efecto real (D7, F2c, cerrada por H-016 con `ejecutar_con_corte`): la
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


def _leer_revocada_para_reintentar(
    fabrica: Any, *, administracion_id: UUID, invitacion_id: UUID
) -> str | None:
    """RB2b-post-1 (revisión backend post-rompedor): el `clerk_invitacion_id`
    si la fila quedó `revocada` con un id guardado; `None` si la fila no
    existe, si no está `revocada` (volvió a `pendiente` por otra vía, o
    quedó `enviada`/`fallida`) o si nunca llegó a guardar un id (la
    revocación ganó la carrera antes de que este trabajo mandara nada a
    Clerk: no hay nada que revocar). Lo usa el reintento de
    `enviar_invitacion` cuando `_leer_invitacion_para_enviar` ya no
    encuentra la fila `pendiente` (línea 224): la revocación INLINE del
    primer intento (R2B-1, más abajo) pudo haber fallado con un error
    pasajero y, sin este chequeo, ese reintento devuelve `True` sin volver
    a intentarla, dejando la invitación abierta en Clerk para siempre."""
    with abrir_sesion(fabrica, administracion_id) as sesion:
        fila = sesion.execute(
            text(
                "SELECT estado, clerk_invitacion_id FROM invitacion "
                "WHERE id=:invitacion AND administracion_id=:admin"
            ),
            {"invitacion": str(invitacion_id), "admin": str(administracion_id)},
        ).first()
        sesion.rollback()
    if fila is None or fila.estado != "revocada" or fila.clerk_invitacion_id is None:
        return None
    clerk_id: str = fila.clerk_invitacion_id
    return clerk_id


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
        # RB2b-post-1: este reintento puede ser justo el que sigue a una
        # revocación en carrera cuya revocación inline (más abajo) falló
        # con un error pasajero. Si quedó `revocada` con un id guardado,
        # todavía hay algo que revocar en Clerk antes de dar el trabajo
        # por terminado.
        clerk_id_pendiente_de_revocar = await asyncio.to_thread(
            _leer_revocada_para_reintentar,
            fabrica,
            administracion_id=argumentos.administracion_id,
            invitacion_id=argumentos.invitacion_id,
        )
        if clerk_id_pendiente_de_revocar is None:
            return True
        clerk_de_reintento: ClienteDeClerk | None = ctx["clerk"]
        if clerk_de_reintento is None:
            raise ErrorPasajero("CLERK_SECRET_KEY no configurada")
        try:
            await clerk_de_reintento.revocar(clerk_id_pendiente_de_revocar)
        except ClerkRechazoDefinitivo:
            # 404 o "ya revocada": idéntico criterio al de la revocación
            # inline de más abajo, cuenta como éxito.
            pass
        except ClerkNoDisponible as error:
            raise ErrorPasajero("clerk no disponible") from error
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


# --- 7, H-015: el PDF de la expensa (E12) ----------------------------------
#
# La primera tarea con un efecto de plata sobre la base que pasa por `ejecutar_con_corte` (H-016,
# F2c, D-158). La idempotencia es la del propio documento: `generar_documento` no hace nada sobre un
# `generado` y toma la fila con `FOR UPDATE`, así que un reencolado (el barrido, un reproceso, un
# reintento) nunca archiva dos versiones. La `clave` de `trabajos_hechos` lleva el origen del
# encolado (`pdf:<documento>:<origen>`): un reproceso trae una nueva y no choca con la de un intento
# anterior que dejó el documento `fallido`.

#: Cota propia de la generación del PDF: WeasyPrint arma una página en menos de dos segundos; la
#: cota la corta en la base (la transacción está abierta mientras se dibuja) y es menor que el
#: `job_timeout` de la tarea (60 s en `AjustesDelWorker`).
COTA_GENERAR_PDF_S = 30.0

#: Una pasada del barrido reencola hasta esto, de a poco (el resto, en la siguiente).
LIMITE_DEL_BARRIDO = 200
#: Un documento recién creado tiene su encolado de la emisión en camino: el barrido espera a que
#: tenga esta antigüedad (segundos) antes de reencolarlo.
ANTIGUEDAD_DEL_BARRIDO_S = 120
#: Ancho (segundos) del origen `b<n>` de las claves del barrido: dos pasadas dentro del mismo tramo
#: se deduplican en ARQ.
TRAMO_DEL_BARRIDO_S = 300


class _ArgumentosGenerarPdf(BaseModel):
    model_config = ConfigDict(strict=True)

    administracion_id: UUID
    documento_id: UUID

    _ids_desde_texto = field_validator("documento_id", mode="before")(_uuid_desde_texto)


def _generar_en_un_hilo(
    fabrica: Any, *, administracion_id: UUID, documento_id: UUID, clave: str, request_id: str
) -> bool:
    from proptech_core.liquidacion.aplicacion.documentos import generar_documento

    return ejecutar_con_corte(
        fabrica,
        administracion_id=administracion_id,
        cota_s=COTA_GENERAR_PDF_S,
        clave=clave,
        tarea=NOMBRE_TAREA_DEL_PDF,
        request_id=request_id,
        efecto=lambda sesion: generar_documento(sesion, documento_id=documento_id),
    )


NOMBRE_TAREA_DEL_PDF = "generar_pdf_de_expensa"


@con_seguimiento_de_tarea
@con_administracion_de_tarea
@reintentable
async def generar_pdf_de_expensa(
    ctx: dict[str, Any],
    *,
    request_id: str,
    clave: str,
    administracion_id: UUID,
    documento_id: Any,
    **datos: Any,
) -> bool:
    """`generar_pdf_de_expensa(administracion_id, documento_id)`: genera y archiva el PDF de un
    documento a través de `ejecutar_con_corte`, con el tenant de la administración. Devuelve `False`
    si esa `clave` ya estaba hecha. Un documento que no se puede armar queda `fallido` con su motivo
    (sin reintentar a ciegas: lo reprocesa una persona); un corte de la base es pasajero."""
    try:
        argumentos = _ArgumentosGenerarPdf(
            administracion_id=administracion_id, documento_id=documento_id
        )
    except ValidationError as error:
        campo = error.errors()[0]["loc"][0]
        raise ArgumentoDeTareaInvalido(f"generar_pdf_de_expensa: {campo}") from None
    return await asyncio.wait_for(
        asyncio.to_thread(
            _generar_en_un_hilo,
            ctx["fabrica_de_sesiones"],
            administracion_id=argumentos.administracion_id,
            documento_id=argumentos.documento_id,
            clave=clave,
            request_id=request_id,
        ),
        timeout=COTA_GENERAR_PDF_S + MARGEN_DE_ESPERA_S,
    )


# --- 14, H-037: la IA completa la factura (R12, R23, D-169) ---
#
# La lectura de una factura subida: llama al lector de IA (el puerto `LectorDeFacturaConIa`, que el
# worker arma al arrancar con OpenRouter, o `None` sin configurar) y deja el resultado en el gasto y
# su costo en `llamada_de_ia`, todo en una transacción a través de `ejecutar_con_corte`. Una falla
# del lector no se reintenta a ciegas (cobraría de nuevo): deja el gasto `sin_ia` y la persona lo
# completa. La `clave` lleva el origen del encolado (`lectura:<gasto>:<origen>`).

NOMBRE_TAREA_DE_LA_LECTURA = "leer_factura_con_ia"

#: Cota propia de la lectura: la llamada a OpenRouter tiene su propio plazo (30 s) y la transacción
#: espera abierta mientras tanto, así que la cota la deja respirar. Menor que el `timeout` de la
#: tarea (90 s en `AjustesDelWorker`).
COTA_LEER_FACTURA_S = 60.0


class _ArgumentosLeerFactura(BaseModel):
    model_config = ConfigDict(strict=True)

    administracion_id: UUID
    gasto_id: UUID

    _ids_desde_texto = field_validator("gasto_id", mode="before")(_uuid_desde_texto)


def _leer_en_un_hilo(
    fabrica: Any,
    lector: Any,
    *,
    administracion_id: UUID,
    gasto_id: UUID,
    clave: str,
    request_id: str,
) -> bool:
    from proptech_core.gastos.aplicacion.lectura_de_factura import leer_la_factura

    return ejecutar_con_corte(
        fabrica,
        administracion_id=administracion_id,
        cota_s=COTA_LEER_FACTURA_S,
        clave=clave,
        tarea=NOMBRE_TAREA_DE_LA_LECTURA,
        request_id=request_id,
        efecto=lambda sesion: leer_la_factura(
            sesion,
            administracion_id=administracion_id,
            gasto_id=gasto_id,
            clave=clave,
            lector=lector,
        ),
    )


@con_seguimiento_de_tarea
@con_administracion_de_tarea
@reintentable
async def leer_factura_con_ia(
    ctx: dict[str, Any],
    *,
    request_id: str,
    clave: str,
    administracion_id: UUID,
    gasto_id: Any,
    **datos: Any,
) -> bool:
    """`leer_factura_con_ia(administracion_id, gasto_id)`: completa el borrador de una factura con
    la IA (`ctx["lector_de_facturas"]`, o `None` si no hay IA configurada). Devuelve `False` si esa
    `clave` ya estaba hecha. Un corte de la base es pasajero y se reintenta; una falla de la IA deja
    el gasto `sin_ia` con su motivo."""
    try:
        argumentos = _ArgumentosLeerFactura(administracion_id=administracion_id, gasto_id=gasto_id)
    except ValidationError as error:
        campo = error.errors()[0]["loc"][0]
        raise ArgumentoDeTareaInvalido(f"leer_factura_con_ia: {campo}") from None
    return await asyncio.wait_for(
        asyncio.to_thread(
            _leer_en_un_hilo,
            ctx["fabrica_de_sesiones"],
            ctx.get("lector_de_facturas"),
            administracion_id=argumentos.administracion_id,
            gasto_id=argumentos.gasto_id,
            clave=clave,
            request_id=request_id,
        ),
        timeout=COTA_LEER_FACTURA_S + MARGEN_DE_ESPERA_S,
    )


def _pendientes_de_todas_las_administraciones(fabrica: Any) -> dict[UUID, list[UUID]]:
    from proptech_core.compartido.base_de_datos import abrir_sesion_del_barrido_de_documentos
    from proptech_core.liquidacion.aplicacion.documentos import pendientes_del_barrido

    with abrir_sesion_del_barrido_de_documentos(fabrica) as sesion:
        pendientes = pendientes_del_barrido(
            sesion, antiguedad_s=ANTIGUEDAD_DEL_BARRIDO_S, limite=LIMITE_DEL_BARRIDO
        )
        sesion.rollback()
    por_administracion: dict[UUID, list[UUID]] = {}
    for administracion, documento in pendientes:
        por_administracion.setdefault(administracion, []).append(documento)
    return por_administracion


@con_seguimiento_de_tarea
async def _barrer_documentos_pendientes(
    ctx: dict[str, Any], *, request_id: str, ahora_s: float
) -> int:
    from proptech_core.liquidacion.aplicacion.documentos import encolar_generacion

    por_administracion = await asyncio.to_thread(
        _pendientes_de_todas_las_administraciones, ctx["fabrica_de_sesiones"]
    )
    origen = f"b{int(ahora_s // TRAMO_DEL_BARRIDO_S)}"
    encolados = 0
    for administracion, documentos in por_administracion.items():
        encolados += await encolar_generacion(
            ctx["cola"],
            administracion_id=administracion,
            documentos=documentos,
            request_id=UUID(request_id),
            origen=origen,
        )
    return encolados


async def barrido_de_documentos_pendientes(ctx: dict[str, Any]) -> int:
    """El barrido periódico (`cron_jobs` de ARQ, E12): reencola los documentos `pendiente` de todas
    las administraciones, los que quedaron así porque Redis no estaba al emitir o porque la
    generación se agotó. Generar dos veces un documento es inofensivo."""
    return await _barrer_documentos_pendientes(
        ctx, request_id=str(uuid.uuid4()), ahora_s=time.time()
    )
