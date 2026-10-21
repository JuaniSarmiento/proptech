"""D6/D7: generar, persistir y encolar sin transportar el token crudo ni el email."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.sobres import generar
from proptech_core.acceso.puertos import ColaDeInvitaciones
from proptech_core.compartido.parametros import Parametros


def crear_invitacion(
    sesion: Session,
    identidad: Identidad,
    persona_id: UUID,
    parametros: Parametros,
    clave: SecretStr,
) -> tuple[UUID, str]:
    vence = datetime.now(UTC) + timedelta(days=parametros.invitaciones.vencimiento_dias)
    resumen, sobre = generar(clave, vence)
    id_ = sesion.execute(
        text(
            "INSERT INTO invitacion (administracion_id,persona_id,"
            "estado,token_resumen,vence,creada_por) VALUES (:admin,:persona,'pendiente',"
            ":resumen,:vence,:actor) RETURNING id"
        ),
        {
            "admin": identidad.administracion_id,
            "persona": persona_id,
            "resumen": resumen,
            "vence": vence,
            "actor": identidad.persona_id,
        },
    ).scalar_one()
    return id_, sobre


#: Retención ARQ del trabajo (D7, RB2b-7): si nunca corre, expira a la hora;
#: un intento ya iniciado puede retenerlo hasta `job_timeout` más (30 s).
EXPIRA_EN_S = 3600


async def encolar_envio(
    cola: ColaDeInvitaciones, admin: UUID, invitacion: UUID, sobre: str, request_id: UUID
) -> None:
    await cola.encolar(
        "enviar_invitacion",
        clave=f"invitacion:{invitacion}",
        request_id=str(request_id),
        expira_en_s=EXPIRA_EN_S,
        administracion_id=str(admin),
        invitacion_id=str(invitacion),
        sobre=sobre,
    )
