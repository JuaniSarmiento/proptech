"""D5/D7: personas y asignaciones del tenant, con invitación y auditoría atómicas."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.aplicacion.entrega import EXPIRA_EN_S, crear_invitacion, encolar_envio
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.permisos import (
    POR_DEBAJO_DEL_ADMINISTRADOR_PRINCIPAL,
    Asignacion,
    Rol,
)
from proptech_core.acceso.puertos import ColaDeInvitaciones
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.parametros import Parametros


class ConflictoDeAcceso(Exception):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__("conflicto")


@dataclass(frozen=True)
class AltaDeUsuario:
    persona_id: UUID
    asignacion_id: UUID
    invitacion_id: UUID | None
    sobre: str | None = field(repr=False)
    revocadas: tuple[UUID, ...]


def _persona_bloqueada(
    sesion: Session, admin: UUID, nombre: str, email: str
) -> tuple[UUID, str | None]:
    # D12 (2d, 7.7): reinvitar el mismo email deja el nombre nuevo, salvo
    # que esa persona ya tenga una asignación de super admin (R2D-3) — con
    # el WHERE falso, Postgres no actualiza pero igual bloquea la fila, y el
    # `SELECT ... FOR UPDATE` de abajo sigue sus reglas de siempre. El
    # `administracion_id = :admin` del conflicto y la RLS de `persona` (sólo
    # las filas del tenant en uso) dejan afuera a otra administración.
    sesion.execute(
        text(
            "INSERT INTO persona (administracion_id,nombre,email) VALUES "
            "(:admin,:nombre,:email) "
            "ON CONFLICT (administracion_id,email) DO UPDATE SET nombre = EXCLUDED.nombre "
            "WHERE NOT EXISTS (SELECT 1 FROM asignacion_rol a "
            "WHERE a.persona_id = persona.id AND a.rol = 'super_admin')"
        ),
        {"admin": admin, "nombre": nombre, "email": email},
    )
    fila = sesion.execute(
        text("SELECT id,clerk_usuario_id FROM persona WHERE email=:email FOR UPDATE"),
        {"email": email},
    ).one()
    return fila.id, fila.clerk_usuario_id


def _alta(
    sesion: Session,
    identidad: Identidad,
    *,
    nombre: str,
    email: str,
    rol: str,
    alcance: str,
    complejo_id: UUID | None,
    parametros: Parametros,
    configuracion: Configuracion,
    request_id: UUID,
    unidad_id: UUID | None = None,
    vinculo: str | None = None,
    evento: EventoDeAcceso = EventoDeAcceso.INVITAR_PERSONAL,
) -> AltaDeUsuario:
    try:
        with sesion.begin_nested():
            persona, clerk_id = _persona_bloqueada(
                sesion, identidad.administracion_id, nombre, email
            )
            asignacion = sesion.execute(
                text(
                    "INSERT INTO asignacion_rol (administracion_id,persona_id,"
                    "rol,complejo_id,unidad_id,vinculo) "
                    "VALUES (:admin,:persona,:rol,:complejo,:unidad,:vinculo) RETURNING id"
                ),
                {
                    "admin": identidad.administracion_id,
                    "persona": persona,
                    "rol": rol,
                    "complejo": complejo_id,
                    "unidad": unidad_id,
                    "vinculo": vinculo,
                },
            ).scalar_one()
            revocadas: tuple[UUID, ...] = ()
            invitacion, sobre = None, None
            if clerk_id is None:
                revocadas = tuple(
                    sesion.execute(
                        text(
                            "UPDATE invitacion SET estado='revocada' "
                            "WHERE persona_id=:persona "
                            "AND estado IN ('pendiente','enviada','fallida') "
                            "RETURNING id"
                        ),
                        {"persona": persona},
                    ).scalars()
                )
                invitacion, sobre = crear_invitacion(
                    sesion, identidad, persona, parametros, configuracion.clave_para_invitar()
                )
            registrar(
                sesion,
                identidad,
                evento,
                entidad="persona",
                entidad_id=persona,
                request_id=request_id,
                detalle={
                    "persona_id": str(persona),
                    "asignacion_id": str(asignacion),
                    **({"rol": rol, "alcance": alcance} if unidad_id is None else {}),
                },
            )
            return AltaDeUsuario(persona, asignacion, invitacion, sobre, revocadas)
    except IntegrityError as error:
        if isinstance(error.orig, UniqueViolation) and error.orig.diag.constraint_name in {
            "uq_asignacion_rol_persona_alcance",
            "uq_asignacion_rol_consejo_persona_complejo",
            "uq_asignacion_rol_persona_unidad",
        }:
            raise ConflictoDeAcceso("vinculo" if unidad_id is not None else "rol") from None
        raise


async def encolar_alta(
    cola: ColaDeInvitaciones, identidad: Identidad, alta: AltaDeUsuario, request_id: UUID
) -> None:
    for id_ in alta.revocadas:
        await cola.encolar(
            "revocar_invitacion_en_clerk",
            clave=f"revocar:{id_}",
            request_id=str(request_id),
            expira_en_s=EXPIRA_EN_S,
            administracion_id=str(identidad.administracion_id),
            invitacion_id=str(id_),
        )
    if alta.invitacion_id is not None and alta.sobre is not None:
        await encolar_envio(
            cola, identidad.administracion_id, alta.invitacion_id, alta.sobre, request_id
        )


def invitar_personal(
    sesion: Session,
    identidad: Identidad,
    *,
    nombre: str,
    email: str,
    rol: str,
    alcance: str,
    complejo_id: UUID | None,
    parametros: Parametros,
    configuracion: Configuracion,
    request_id: UUID,
) -> AltaDeUsuario:
    return _alta(
        sesion,
        identidad,
        nombre=nombre,
        email=email,
        rol=rol,
        alcance=alcance,
        complejo_id=complejo_id,
        parametros=parametros,
        configuracion=configuracion,
        request_id=request_id,
    )


def dar_de_alta_vecino(
    sesion: Session,
    identidad: Identidad,
    *,
    nombre: str,
    email: str,
    vinculo: str,
    complejo_id: UUID,
    unidad_id: UUID,
    parametros: Parametros,
    configuracion: Configuracion,
    request_id: UUID,
) -> AltaDeUsuario:
    return _alta(
        sesion,
        identidad,
        nombre=nombre,
        email=email,
        rol="vecino",
        alcance="unidad",
        complejo_id=complejo_id,
        unidad_id=unidad_id,
        vinculo=vinculo,
        parametros=parametros,
        configuracion=configuracion,
        request_id=request_id,
        evento=EventoDeAcceso.DAR_DE_ALTA_VECINO,
    )


class InvitacionNoRevocable(Exception):
    """No está abierta (`pendiente`/`enviada`/`fallida`) o es de otra
    administración: RLS ya la filtra, da el mismo caso que no existir."""


class AsignacionNoEncontrada(Exception):
    """De otra administración (RLS) o directamente inexistente."""


def _todas_por_debajo(asignaciones_crudas: list[Any]) -> bool:
    """D13: "todas sus asignaciones son de abajo", verdadero para la lista
    vacía (`all([])`) — por eso el llamador exige además "al menos una"
    (R2D-2): una persona sin asignaciones no cuenta como "de abajo"."""
    for fila in asignaciones_crudas:
        asignacion = Asignacion(
            rol=Rol(fila.rol),
            complejo_id=fila.complejo_id,
            unidad_id=fila.unidad_id,
            vinculo=fila.vinculo,
        )
        if (asignacion.perfil, asignacion.alcance) not in POR_DEBAJO_DEL_ADMINISTRADOR_PRINCIPAL:
            return False
    return True


def listar_personal(sesion: Session, *, solo_por_debajo: bool = False) -> list[dict[str, Any]]:
    """D5: personas, sus asignaciones y la invitación más reciente, sólo de
    la administración (RLS, nunca un `WHERE` propio). `vencida` se calcula
    acá: una invitación abierta (`pendiente`/`enviada`/`fallida`) cuyo
    `vence` ya pasó, nunca se reescribe sola en la base.

    `solo_por_debajo` (D13, 2d grupo 7): para el administrador principal,
    filtra a las personas con al menos una asignación y cuyas asignaciones
    son todas de administrador por edificio, contador, auxiliar o consejo
    (`POR_DEBAJO_DEL_ADMINISTRADOR_PRINCIPAL`, la misma lista que la matriz
    de permisos declara, nunca una copia). El super admin no filtra: trae lo
    de siempre."""
    ahora = datetime.now(UTC)
    personas = sesion.execute(
        text("SELECT id, nombre, email, clerk_usuario_id FROM persona ORDER BY nombre")
    ).all()
    asignaciones: dict[UUID, list[dict[str, Any]]] = {}
    asignaciones_crudas: dict[UUID, list[Any]] = {}
    for fila in sesion.execute(
        text("SELECT id, persona_id, rol, complejo_id, unidad_id, vinculo FROM asignacion_rol")
    ):
        asignaciones.setdefault(fila.persona_id, []).append(
            {
                "asignacion_id": str(fila.id),
                "rol": fila.rol,
                "complejo_id": str(fila.complejo_id) if fila.complejo_id else None,
                "unidad_id": str(fila.unidad_id) if fila.unidad_id else None,
                "vinculo": fila.vinculo,
            }
        )
        asignaciones_crudas.setdefault(fila.persona_id, []).append(fila)
    invitaciones: dict[UUID, dict[str, Any]] = {}
    for fila in sesion.execute(
        text(
            "SELECT DISTINCT ON (persona_id) persona_id, id, estado, vence FROM invitacion "
            "ORDER BY persona_id, creada_en DESC"
        )
    ):
        estado = fila.estado
        if estado in ("pendiente", "enviada", "fallida") and fila.vence <= ahora:
            estado = "vencida"
        invitaciones[fila.persona_id] = {"invitacion_id": str(fila.id), "estado": estado}
    resultado = []
    for p in personas:
        crudas = asignaciones_crudas.get(p.id, [])
        if solo_por_debajo and (not crudas or not _todas_por_debajo(crudas)):
            continue
        resultado.append(
            {
                "persona_id": str(p.id),
                "nombre": p.nombre,
                "email": p.email,
                "vinculado": p.clerk_usuario_id is not None,
                "asignaciones": asignaciones.get(p.id, []),
                "invitacion": invitaciones.get(p.id),
            }
        )
    return resultado


def revocar_invitacion(
    sesion: Session, identidad: Identidad, invitacion_id: UUID, request_id: UUID
) -> None:
    """D5/D7: revoca sólo si sigue abierta; el worker avisa a Clerk después
    (`encolar_revocacion`), nunca acá adentro de la transacción."""
    fila = sesion.execute(
        text(
            "UPDATE invitacion SET estado = 'revocada' "
            "WHERE id = :invitacion AND estado IN ('pendiente', 'enviada', 'fallida') "
            "RETURNING persona_id"
        ),
        {"invitacion": invitacion_id},
    ).first()
    if fila is None:
        sesion.rollback()
        raise InvitacionNoRevocable
    registrar(
        sesion,
        identidad,
        EventoDeAcceso.REVOCAR_INVITACION,
        entidad="invitacion",
        entidad_id=invitacion_id,
        request_id=request_id,
        detalle={},
    )
    sesion.commit()


async def encolar_revocacion(
    cola: ColaDeInvitaciones, identidad: Identidad, invitacion_id: UUID, request_id: UUID
) -> None:
    await cola.encolar(
        "revocar_invitacion_en_clerk",
        clave=f"revocar:{invitacion_id}",
        request_id=str(request_id),
        expira_en_s=EXPIRA_EN_S,
        administracion_id=str(identidad.administracion_id),
        invitacion_id=str(invitacion_id),
    )


def quitar_asignacion(
    sesion: Session, identidad: Identidad, asignacion_id: UUID, request_id: UUID
) -> None:
    """D5: el único super admin no puede perder su única asignación (409,
    `ConflictoDeAcceso("super_admin")`); cualquier otra, con o sin ella la
    persona sigue teniendo alguna, se quita sin más condición."""
    fila = sesion.execute(
        text("SELECT persona_id, rol FROM asignacion_rol WHERE id = :asignacion"),
        {"asignacion": asignacion_id},
    ).first()
    if fila is None:
        sesion.rollback()
        raise AsignacionNoEncontrada
    if fila.rol == "super_admin":
        # R2B-2: `FOR UPDATE` bloquea las filas de super admin de la
        # administración ANTES de contarlas (Postgres no admite `FOR
        # UPDATE` junto a un `count(*)`, así que se cuentan las filas ya
        # traídas). Sin este bloqueo, dos pedidos que se quitan a la vez
        # leen el mismo `count` con MVCC (sin candado) y los dos deciden
        # que queda otro super admin; con el bloqueo, el segundo pedido
        # espera al `DELETE` (o rollback) del primero y vuelve a contar
        # sobre lo que de verdad queda.
        super_admins = sesion.execute(
            text("SELECT id FROM asignacion_rol WHERE rol = 'super_admin' FOR UPDATE")
        ).all()
        if len(super_admins) <= 1:
            sesion.rollback()
            raise ConflictoDeAcceso("super_admin")
    sesion.execute(
        text("DELETE FROM asignacion_rol WHERE id = :asignacion"), {"asignacion": asignacion_id}
    )
    registrar(
        sesion,
        identidad,
        EventoDeAcceso.QUITAR_ASIGNACION,
        entidad="persona",
        entidad_id=fila.persona_id,
        request_id=request_id,
        detalle={},
    )
    sesion.commit()
