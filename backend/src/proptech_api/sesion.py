"""D3: consultar la sesión sin persona; registrar el ingreso con identidad."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from proptech_api.acceso import (
    RutaConIdentidad,
    RutaConTokenVerificado,
    identidad_actual,
    sesion_con_tenant,
    token_de_sesion_actual,
)
from proptech_api.errores import sin_acceso_http
from proptech_core.acceso.aplicacion.identidad import SinAcceso
from proptech_core.acceso.aplicacion.sesion import consultar, registrar_ingreso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.dominio.token import TokenVerificado
from proptech_core.compartido.seguimiento import request_id_actual

router = APIRouter(prefix="/api", route_class=RutaConIdentidad)
router_de_token = APIRouter(prefix="/api", route_class=RutaConTokenVerificado)


@router_de_token.get("/sesion")
def sesion_actual(
    request: Request, token: TokenVerificado = Depends(token_de_sesion_actual)
) -> dict[str, Any]:
    try:
        return consultar(request.app.state.fabrica_de_sesiones, token.sub)
    except SinAcceso:
        raise sin_acceso_http() from None


@router.post("/sesion/ingreso")
def ingreso(
    identidad: Identidad = Depends(identidad_actual), sesion: Session = Depends(sesion_con_tenant)
) -> dict[str, bool]:
    registrar_ingreso(sesion, identidad, UUID(request_id_actual.get() or ""))
    return {"registrado": True}
