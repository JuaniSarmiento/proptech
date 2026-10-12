"""Crea la app FastAPI con el router bajo /api."""

from fastapi import APIRouter, FastAPI

from proptech_api import salud
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.parametros import leer_parametros


def crear_app() -> FastAPI:
    # Falla rápido: si falta una variable de configuración, el proceso termina
    # acá, nombrando la variable (D11 / spec "API sin cadena de conexión"). Sin
    # esto, Configuracion() se construye recién dentro del verificador de salud,
    # su excepción queda atrapada por el `except Exception` genérico del
    # endpoint y un error de configuración se confunde con la base caída.
    configuracion = Configuracion()
    # Idem con los parámetros del sistema (D6): un archivo inválido también
    # termina el arranque acá, nombrando cada campo con problemas.
    leer_parametros(configuracion.proptech_parametros)

    app = FastAPI(title="PropTech API")
    router_api = APIRouter(prefix="/api")
    router_api.include_router(salud.router)
    app.include_router(router_api)
    return app


app = crear_app()
