"""Lectura de `config/georef/` (D1, tarea 2.5): tres rutas públicas del país,
sin tenant ni rol — sólo exigen sesión válida (`identidad_actual`, 401 sin
ella). Nunca dependen de un complejo ni de un permiso."""

from fastapi import APIRouter, Depends, HTTPException, Request

from proptech_api.acceso import RutaConIdentidad, identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

router = APIRouter(prefix="/api/georef", route_class=RutaConIdentidad)


@router.get("/provincias")
def provincias(
    request: Request, identidad: Identidad = Depends(identidad_actual)
) -> list[dict[str, str]]:
    georef = request.app.state.georef
    return [{"id": p.id, "nombre": p.nombre} for p in georef.listar_provincias()]


@router.get("/provincias/{provincia_id}/departamentos")
def departamentos(
    provincia_id: str,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
) -> list[dict[str, str]]:
    georef = request.app.state.georef
    departamentos = georef.departamentos_de(provincia_id)
    if departamentos is None:
        raise HTTPException(status_code=404, detail="no encontrado")
    return [{"id": d.id, "nombre": d.nombre} for d in departamentos]


@router.get("/departamentos/{departamento_id}/localidades")
def localidades(
    departamento_id: str,
    request: Request,
    identidad: Identidad = Depends(identidad_actual),
) -> list[dict[str, str]]:
    georef = request.app.state.georef
    localidades = georef.localidades_de(departamento_id)
    if localidades is None:
        raise HTTPException(status_code=404, detail="no encontrado")
    return [{"id": loc.id, "nombre": loc.nombre} for loc in localidades]
