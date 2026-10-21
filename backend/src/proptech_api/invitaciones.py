"""D3/D6: aceptación por token de sesión, anterior al vínculo de persona."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from proptech_api.acceso import RutaConTokenVerificado, token_de_sesion_actual
from proptech_api.cuerpos import CuerpoDeAlta
from proptech_core.acceso.aplicacion.invitaciones import InvitacionNoDisponible, aceptar
from proptech_core.acceso.dominio.token import TokenVerificado
from proptech_core.compartido.seguimiento import request_id_actual

router_de_token = APIRouter(prefix="/api", route_class=RutaConTokenVerificado)


class CuerpoAceptar(CuerpoDeAlta):
    token: str


@router_de_token.post("/invitaciones/aceptar")
def aceptar_invitacion(
    request: Request,
    cuerpo: CuerpoAceptar,
    token: TokenVerificado = Depends(token_de_sesion_actual),
) -> dict[str, bool]:
    try:
        aceptar(
            request.app.state.fabrica_de_sesiones,
            token,
            cuerpo.token,
            request.app.state.configuracion,
            UUID(request_id_actual.get() or ""),
        )
    except InvitacionNoDisponible:
        raise HTTPException(404, detail="no encontrado") from None
    return {"aceptada": True}
