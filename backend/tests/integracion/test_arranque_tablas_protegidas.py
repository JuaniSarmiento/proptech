"""D3: los cuatro consumidores frenan antes de operar con tablas sin proteger."""

import asyncio
import importlib
import os
import sys
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from proptech_api.app import crear_app
from proptech_core.compartido.base_de_datos import (
    TablasDeSoloAgregarDesprotegidas,
    verificar_tablas_de_solo_agregar,
)
from proptech_core.compartido.configuracion import Configuracion

from ..conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION
from ._edificios import BaseDeEdificio
from .test_propiedad_protegida import devolver_configuracion
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


@pytest.fixture(autouse=True)
def conservar_modulo_worker() -> Any:
    previo = sys.modules.get("proptech_worker.ajustes")
    estado = dict(previo.__dict__) if previo is not None else None
    try:
        yield
    finally:
        if previo is None:
            sys.modules.pop("proptech_worker.ajustes", None)
        elif estado is not None:
            previo.__dict__.clear()
            previo.__dict__.update(estado)


def entorno(base: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in base.entorno.items():
        if k in {"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB"}:
            monkeypatch.setenv(k, v)
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    monkeypatch.setenv("PROPTECH_ENTORNO", "desarrollo")


@pytest.mark.parametrize("consumidor", ["api", "worker", "alta_inicial", "ejemplo"])
def test_cada_proceso_frena(
    base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch, consumidor: str
) -> None:
    base = base_del_edificio
    entorno(base, monkeypatch)
    devolver_configuracion(base)
    registros: list[dict[str, Any]] = []
    logger = None
    if consumidor == "api":
        import proptech_api.app as modulo_api

        logger = modulo_api._logger
    elif consumidor == "worker":
        import proptech_worker.ajustes as modulo_worker

        modulo_worker = importlib.reload(modulo_worker)
        logger = modulo_worker._logger
    if logger is not None:

        def registrar_error(mensaje: str, *, extra: dict[str, Any]) -> None:
            registros.append({"evento": mensaje, **extra})

        monkeypatch.setattr(logger, "error", registrar_error)
    try:
        with pytest.raises(TablasDeSoloAgregarDesprotegidas, match="configuracion_versionada"):
            if consumidor == "api":
                with TestClient(crear_app()):
                    pass
            elif consumidor == "worker":
                import proptech_worker.ajustes as worker

                worker = importlib.reload(worker)
                asyncio.run(worker.on_startup({}))
            elif consumidor == "alta_inicial":
                from proptech_core.acceso.aplicacion import alta_inicial

                async def no_operar(*args: Any, **kwargs: Any) -> Any:
                    return uuid4()

                monkeypatch.setattr(alta_inicial, "crear", no_operar)
                monkeypatch.setattr(
                    sys,
                    "argv",
                    [
                        "alta_inicial",
                        "--administracion",
                        "Ficticia",
                        "--nombre",
                        "Ficticio",
                        "--email",
                        "ficticio@example.test",
                    ],
                )
                alta_inicial.main()
            else:
                from proptech_core.complejos.aplicacion import ejemplo

                monkeypatch.setattr(
                    ejemplo,
                    "cargar",
                    lambda *a, **kw: ejemplo.ResultadoCarga(uuid4(), uuid4(), False),
                )
                ejemplo._main(["cargar"])
        if consumidor in {"api", "worker"}:
            assert len(registros) == 1
            assert registros[0]["evento"] == "arranque_fallido"
            assert "configuracion_versionada" in registros[0]["causa"]
            assert "clave" not in registros[0]["causa"]
    finally:
        base.roles("despues")


def test_esquema_exacto_y_tabla_ausente(
    base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = base_del_edificio
    entorno(base, monkeypatch)
    engine = create_engine(Configuracion().url_sqlalchemy())
    try:
        verificar_tablas_de_solo_agregar(engine)
        with arranque(base) as c:
            c.execute("CREATE SCHEMA homonimo")
            c.execute("CREATE TABLE homonimo.configuracion_versionada (id int)")
            devolver_configuracion(base)
            try:
                with pytest.raises(
                    TablasDeSoloAgregarDesprotegidas, match="configuracion_versionada"
                ):
                    with TestClient(crear_app()):
                        pass
            finally:
                c.execute("DROP SCHEMA homonimo CASCADE")
                base.roles("despues")
            c.execute("ALTER TABLE public.configuracion_versionada RENAME TO configuracion_oculta")
            try:
                with pytest.raises(
                    TablasDeSoloAgregarDesprotegidas, match="configuracion_versionada"
                ):
                    verificar_tablas_de_solo_agregar(engine)
            finally:
                c.execute("ALTER TABLE configuracion_oculta RENAME TO configuracion_versionada")
    finally:
        engine.dispose()


def test_conjunto_coincide_con_catalogo(base_del_edificio: BaseDeEdificio) -> None:
    from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

    with arranque(base_del_edificio) as c, c.transaction(force_rollback=True):
        if os.environ.get("PROPTECH_MUTANTE_TABLA_EXTRA") == "1":
            c.execute("CREATE TABLE protegida_olvidada (id int)")
            c.execute("ALTER TABLE protegida_olvidada FORCE ROW LEVEL SECURITY")
            c.execute(
                "CREATE TRIGGER bloqueo BEFORE UPDATE ON protegida_olvidada FOR EACH "
                "STATEMENT EXECUTE FUNCTION fn_configuracion_versionada_bloqueada()"
            )
        candidatas = {
            f[0]
            for f in c.execute(
                "SELECT DISTINCT t.relname FROM pg_class t JOIN pg_namespace n ON "
                "n.oid=t.relnamespace JOIN pg_trigger g ON g.tgrelid=t.oid JOIN pg_proc p "
                "ON p.oid=g.tgfoid WHERE n.nspname='public' AND t.relforcerowsecurity AND "
                "NOT g.tgisinternal AND (g.tgtype::int & 16)<>0 AND p.prosrc ~* "
                "'BEGIN[[:space:]]+RAISE[[:space:]]+EXCEPTION'"
            )
        }
        assert candidatas == set(TABLAS_DE_SOLO_AGREGAR), (
            "tablas protegidas fuera del conjunto: "
            f"{sorted(candidatas ^ set(TABLAS_DE_SOLO_AGREGAR))}"
        )


@pytest.mark.parametrize("consumidor", ["api", "worker"])
def test_procesos_arrancan_con_proteccion(
    base_del_edificio: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch, consumidor: str
) -> None:
    entorno(base_del_edificio, monkeypatch)
    if consumidor == "api":
        app = crear_app()
        with TestClient(app):
            assert app.state.engine is not None
    else:
        import proptech_worker.ajustes as worker

        worker = importlib.reload(worker)
        ctx: dict[str, Any] = {}
        asyncio.run(worker.on_startup(ctx))
        assert "engine" in ctx and "fabrica_de_sesiones" in ctx
        asyncio.run(worker.on_shutdown(ctx))
