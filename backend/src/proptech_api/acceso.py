"""Identidad inyectable y la sesión con tenant (D7, cambio 2a).

`identidad_actual` responde siempre 401, sin tocar la base: hasta el cambio
2b (el login) nadie se puede autenticar de verdad. Los tests la reemplazan
con `app.dependency_overrides[identidad_actual]`.
"""

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import abrir_sesion


def identidad_actual() -> Identidad:
    raise HTTPException(status_code=401)


def sesion_con_tenant(
    request: Request, identidad: Identidad = Depends(identidad_actual)
) -> Iterator[Session]:
    """Depende EXPLÍCITAMENTE de la identidad (D7): así FastAPI no abre la
    sesión antes de saber quién es — si `identidad_actual` levanta 401, esta
    dependencia nunca llega a correr su cuerpo, y ninguna sentencia toca la
    base. El tenant sale sólo de `identidad.administracion_id` (D4): nunca
    de un encabezado, un parámetro o un campo del cuerpo del pedido, aunque
    alguno se llame igual. Como el tenant viaja en `session.info`, da igual
    si esta dependencia es sincrónica o `async def` (D4, punto 5 del
    arquitecto).
    """
    sesion = abrir_sesion(request.app.state.fabrica_de_sesiones, identidad.administracion_id)
    try:
        yield sesion
    finally:
        sesion.close()
