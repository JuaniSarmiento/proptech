"""D6: aceptar la invitación. El tenant sale de la fila que la base
encuentra por el resumen del token (un secreto que sólo tiene el invitado),
nunca de lo que mande el cliente. Cualquier rechazo, sin excepción, es el
mismo `InvitacionNoDisponible` (404 uniforme, sin escribir nada)."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.sobres import SobreInvalido, abrir
from proptech_core.acceso.dominio.token import TokenVerificado
from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    abrir_sesion_por_token_de_invitacion,
)
from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida


class InvitacionNoDisponible(Exception):
    """Respuesta uniforme sin datos del destinatario."""


def aceptar(
    fabrica: sessionmaker[Session],
    token: TokenVerificado,
    sobre: str,
    configuracion: Configuracion,
    request_id: UUID,
) -> None:
    # El email y su verificación son claims YA firmados del token de sesión
    # (D6, RB2b-3): ni `"true"` (texto) ni ausente prueban nada.
    if token.email is None or token.email_verificado is not True:
        raise InvitacionNoDisponible
    try:
        clave = configuracion.clave_para_invitar()
    except ConfiguracionInvalida:
        raise InvitacionNoDisponible from None

    ahora = datetime.now(UTC)
    try:
        token_crudo = abrir(clave, sobre, ahora)
    except SobreInvalido:
        # Sobre alterado, vencido (chequeo propio del sobre) o con una
        # clave que ya no coincide: nunca se reconstruye el token desde su
        # resumen (D7), así que acá termina sin tocar la base.
        raise InvitacionNoDisponible from None
    resumen_hex = hashlib.sha256(token_crudo.encode()).hexdigest()
    email_normalizado = token.email.lower()

    # Primera consulta, SIN tenant (D6): el único candado es el resumen de
    # 64 caracteres hexadecimales, vía `invitacion_por_token` (migración
    # 0020). Nunca el token crudo ni el sobre llegan a una cláusula SQL.
    with abrir_sesion_por_token_de_invitacion(fabrica, resumen_hex) as sesion_sin_tenant:
        fila = sesion_sin_tenant.execute(
            text("SELECT id, administracion_id FROM invitacion WHERE token_resumen = :resumen"),
            {"resumen": bytes.fromhex(resumen_hex)},
        ).first()
        sesion_sin_tenant.rollback()
    if fila is None:
        raise InvitacionNoDisponible
    invitacion_id, administracion_id = fila.id, fila.administracion_id

    # Segunda sesión, CON el tenant que acaba de salir de esa fila (D6): el
    # candado real es el `FOR UPDATE` de abajo, que vuelve a comprobar el
    # resumen bajo el bloqueo (dos aceptaciones a la vez se serializan acá).
    with abrir_sesion(fabrica, administracion_id) as sesion:
        fila_bloqueada = sesion.execute(
            text(
                "SELECT i.estado, i.vence, i.persona_id, p.email, p.clerk_usuario_id "
                "FROM invitacion i "
                "JOIN persona p ON p.administracion_id = i.administracion_id "
                "AND p.id = i.persona_id "
                "WHERE i.id = :invitacion AND i.token_resumen = :resumen "
                "FOR UPDATE OF i"
            ),
            {"invitacion": invitacion_id, "resumen": bytes.fromhex(resumen_hex)},
        ).first()
        if (
            fila_bloqueada is None
            or fila_bloqueada.estado != "enviada"
            or fila_bloqueada.vence <= ahora
            or fila_bloqueada.email.lower() != email_normalizado
            or fila_bloqueada.clerk_usuario_id is not None
        ):
            sesion.rollback()
            raise InvitacionNoDisponible

        persona_id = fila_bloqueada.persona_id
        identidad_ajena = sesion.execute(
            text(
                "SELECT 1 FROM persona WHERE administracion_id = :admin "
                "AND clerk_usuario_id = :sub AND id != :persona"
            ),
            {"admin": administracion_id, "sub": token.sub, "persona": persona_id},
        ).first()
        if identidad_ajena is not None:
            sesion.rollback()
            raise InvitacionNoDisponible

        sesion.execute(
            text(
                "UPDATE persona SET clerk_usuario_id = :sub "
                "WHERE administracion_id = :admin AND id = :persona"
            ),
            {"sub": token.sub, "admin": administracion_id, "persona": persona_id},
        )
        sesion.execute(
            text("UPDATE invitacion SET estado = 'aceptada' WHERE id = :invitacion"),
            {"invitacion": invitacion_id},
        )
        registrar(
            sesion,
            Identidad(administracion_id, persona_id),
            EventoDeAcceso.ACEPTAR_INVITACION,
            entidad="persona",
            entidad_id=persona_id,
            request_id=request_id,
            detalle={},
        )
        sesion.commit()
