"""Crea la app FastAPI con el router bajo /api."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from proptech_api import complejos, salud
from proptech_api.seguimiento import MiddlewareSeguimiento
from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_application_name,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.cola import AdaptadorColaArq
from proptech_core.compartido.conexion_redis import ajustes_redis_arq
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.logs import configurar_logs
from proptech_core.compartido.parametros import leer_parametros


def crear_app() -> FastAPI:
    # Antes que nada: logs en JSON (D7). Uvicorn ya configuró los suyos al
    # importar este módulo; se pisan acá.
    configurar_logs("api")

    # Falla rápido: si falta una variable de configuración, el proceso termina
    # acá, nombrando la variable (D11 / spec "API sin cadena de conexión"). Sin
    # esto, Configuracion() se construye recién dentro del verificador de salud,
    # su excepción queda atrapada por el `except Exception` genérico del
    # endpoint y un error de configuración se confunde con la base caída.
    configuracion = Configuracion()
    # Idem con los parámetros del sistema (D6): un archivo inválido también
    # termina el arranque acá, nombrando cada campo con problemas.
    leer_parametros(configuracion.proptech_parametros)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Un solo engine por proceso (D18, M13): se crea una vez al arrancar,
        # se guarda en app.state y se descarta al cerrar. Antes, /api/salud
        # creaba y descartaba un engine (y su pool) en cada pedido.
        # `application_name=proptech-api` como nombre base de la conexión
        # (D8), gemelo de `proptech-worker` en `proptech_worker/ajustes.py`
        # (L-009): el evento `after_begin` de `registrar_application_name`
        # lo sobreescribe por transacción con el `request_id` en curso.
        engine = crear_engine(configuracion, connect_args={"application_name": "proptech-api"})
        fabrica = crear_fabrica_de_sesiones(engine)
        registrar_application_name(fabrica, "proptech-api")
        # El tenant por transacción (D4, tarea 4.1): lo fija `abrir_sesion`
        # + este evento, nunca un parámetro del pedido.
        registrar_tenant_por_administracion(fabrica)
        # Cinturón además del SET LOCAL de arriba (R7, vuelta 2): una
        # conexión que vuelve al pool nunca lleva el tenant pegado, ni
        # siquiera si algún camino futuro se equivoca y hace un SET de
        # sesión en vez de set_config(..., true).
        registrar_reset_del_tenant_al_devolver(engine)
        app.state.engine = engine
        app.state.fabrica_de_sesiones = fabrica
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="PropTech API", lifespan=lifespan)
    # La cola queda cableada (D4): el pool de ARQ es perezoso (sólo conecta
    # al primer uso), así que armarla acá no intenta hablar con Redis y la
    # app arranca igual aunque esté inalcanzable (tarea 4.7).
    app.state.cola = AdaptadorColaArq(ajustes_redis_arq(configuracion))
    app.add_middleware(MiddlewareSeguimiento)
    # El prefijo "/api" vive en `salud.router` (ver su comentario, F3, vuelta
    # 2 de 1c): pasarlo acá como `include_router(..., prefix=...)`, o anidar
    # un router intermedio sólo para el prefijo, deja a `scope["route"]`
    # (la ruta original, sin el prefijo de inclusión) con un
    # `path_format` relativo, que es lo que filtraba el valor concreto del
    # parámetro en el log (`seguimiento._ruta_de`).
    app.include_router(salud.router)
    app.include_router(complejos.router)
    return app


app = crear_app()
