"""Endpoint de salud: informa si el sistema y la base responden (D11)."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from proptech_core.compartido.base_de_datos import crear_engine, crear_fabrica_de_sesiones
from proptech_core.compartido.configuracion import Configuracion

router = APIRouter()


def _verificador_real() -> bool:
    """Verificador real: SELECT 1 contra la base, timeout de conexión de 2s."""
    configuracion = Configuracion()
    engine = crear_engine(configuracion, connect_args={"connect_timeout": 2})
    try:
        fabrica = crear_fabrica_de_sesiones(engine)
        sesion = fabrica()
        try:
            sesion.execute(text("SELECT 1"))
            return True
        finally:
            sesion.close()
    except SQLAlchemyError:
        return False
    finally:
        engine.dispose()


def obtener_verificador_de_base() -> Callable[[], bool]:
    """Dependencia de FastAPI, inyectable: devuelve el verificador a usar."""
    return _verificador_real


@router.get("/salud")
def salud(
    response: Response,
    verificador: Callable[[], bool] = Depends(obtener_verificador_de_base),
) -> dict[str, str]:
    try:
        base_responde = verificador()
    except Exception:
        base_responde = False

    if base_responde:
        return {"estado": "ok", "base": "ok"}

    response.status_code = 503
    return {"estado": "degradado", "base": "sin_conexion"}
