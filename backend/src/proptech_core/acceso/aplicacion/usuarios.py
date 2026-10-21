"""D5/D7: personas y asignaciones del tenant, con invitación y auditoría atómicas."""

from dataclasses import dataclass, field
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.aplicacion.entrega import crear_invitacion, encolar_envio
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
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
    sesion.execute(
        text(
            "INSERT INTO persona (administracion_id,nombre,email) VALUES "
            "(:admin,:nombre,:email) ON CONFLICT (administracion_id,email) DO NOTHING"
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
