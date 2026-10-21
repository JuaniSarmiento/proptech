"""D6: contrato de aceptación; el vínculo transaccional se completa en 5.5."""

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.dominio.token import TokenVerificado
from proptech_core.compartido.configuracion import Configuracion


class InvitacionNoDisponible(Exception):
    """Respuesta uniforme sin datos del destinatario."""


def aceptar(
    fabrica: sessionmaker[Session],
    token: TokenVerificado,
    sobre: str,
    configuracion: Configuracion,
    request_id: UUID,
) -> None:
    raise InvitacionNoDisponible
