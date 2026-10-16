"""La causa de un arranque rechazado queda en el log (D10, deuda V2-5 del
2a, tarea 6.1). Precondición: 6.0 en verde (el cableado real de R7/R8 ya
está probado sin mocks).

Cuando `Configuracion()` o `verificar_rol_de_aplicacion_seguro` cortan el
arranque de la API o del worker (gemelos, L-009), el log en JSON tiene una
línea con un evento propio de arranque fallido y la causa — nunca ningún
valor secreto (L-007): se prueba con un marcador (una contraseña de
prueba) que no aparece en ningún lado de la salida.

Escenario de `entorno-de-ejecucion`: Arranque rechazado con causa nombrada.
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import RolDeAplicacionInseguro
from proptech_core.compartido.logs import FormateadorJSON

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

#: Con el patrón `proptech_[a-z_]{1,40}` (ver test_cableado_real_del_arranque.py).
ARRANQUE_USER = "proptech_arranque_causa_log"
ARRANQUE_PASSWORD = "clave-arranque-no-real-marcador-7f2c91"
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real-marcador-7f2c91"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


def _eventos_json(salida: str) -> list[dict[str, Any]]:
    eventos = []
    for linea in salida.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            eventos.append(json.loads(linea))
        except ValueError:
            continue
    return eventos


# --- Configuracion() inválida: subproceso, igual que test_arranque_api.py ---


def test_api_logea_arranque_fallido_si_falta_una_variable() -> None:
    entorno = dict(os.environ)
    entorno.pop("POSTGRES_APP_PASSWORD", None)
    entorno.setdefault("POSTGRES_HOST", "db")
    entorno.setdefault("POSTGRES_PORT", "5432")
    entorno.setdefault("POSTGRES_APP_USER", "proptech_app")
    entorno.setdefault("POSTGRES_DB", "proptech")

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_api.app"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0
    eventos = _eventos_json(resultado.stdout)
    fallidos = [e for e in eventos if e.get("evento") == "arranque_fallido"]
    assert len(fallidos) == 1, (
        f"se esperaba exactamente una línea 'arranque_fallido' en stdout: {resultado.stdout!r}"
    )
    assert "POSTGRES_APP_PASSWORD" in fallidos[0].get("causa", "")


def test_worker_logea_arranque_fallido_si_falta_una_variable() -> None:
    """Gemelo (L-009): `proptech_worker.ajustes` corta igual al importarse."""
    entorno = dict(os.environ)
    entorno.pop("POSTGRES_APP_PASSWORD", None)
    entorno.setdefault("POSTGRES_HOST", "db")
    entorno.setdefault("POSTGRES_PORT", "5432")
    entorno.setdefault("POSTGRES_APP_USER", "proptech_app")
    entorno.setdefault("POSTGRES_DB", "proptech")
    entorno.setdefault("REDIS_HOST", "redis")
    entorno.setdefault("REDIS_PORT", "6379")
    entorno.setdefault("REDIS_PASSWORD", "x")

    resultado = subprocess.run(
        [sys.executable, "-c", "import proptech_worker.ajustes"],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert resultado.returncode != 0
    eventos = _eventos_json(resultado.stdout)
    fallidos = [e for e in eventos if e.get("evento") == "arranque_fallido"]
    assert len(fallidos) == 1, (
        f"se esperaba exactamente una línea 'arranque_fallido' en stdout: {resultado.stdout!r}"
    )
    assert "POSTGRES_APP_PASSWORD" in fallidos[0].get("causa", "")


# --- verificar_rol_de_aplicacion_seguro inseguro: contra Postgres real ---


@pytest.fixture(scope="module")
def contenedor() -> Iterator[PostgresContainer]:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username=ARRANQUE_USER,
        password=ARRANQUE_PASSWORD,
    ) as iniciado:
        yield iniciado


def _entorno_de_roles(contenedor: PostgresContainer) -> dict[str, str]:
    return {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD,
        "POSTGRES_APP_USER": APP_USER,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD,
        "POSTGRES_RESPALDO_USER": RESPALDO_USER,
        "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD,
    }


def _alembic_env(contenedor: PostgresContainer) -> dict[str, str]:
    entorno = dict(_entorno_de_roles(contenedor))
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _correr(args: list[str], entorno: dict[str, str]) -> None:
    subprocess.run(args, cwd=RAIZ_BACKEND, env=entorno, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> Iterator[None]:
    _correr(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        _entorno_de_roles(contenedor),
    )
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    try:
        yield
    finally:
        _correr(["uv", "run", "alembic", "downgrade", "base"], _alembic_env(contenedor))


def _capturar_logs_json() -> io.StringIO:
    salida = io.StringIO()
    for handler in logging.getLogger().handlers:
        if isinstance(handler.formatter, FormateadorJSON):
            handler.stream = salida  # type: ignore[attr-defined]
    return salida


def test_api_logea_arranque_fallido_si_el_rol_es_inseguro(
    contenedor: PostgresContainer,
    esquema: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setenv("POSTGRES_HOST", contenedor.get_container_host_ip())
    monkeypatch.setenv("POSTGRES_PORT", str(contenedor.get_exposed_port(5432)))
    # El rol de ARRANQUE (superusuario) como si fuera el de la app: R8 lo
    # rechaza (test_cableado_real_del_arranque.py ya prueba eso); acá lo
    # que importa es que la causa quede en el log, sin la contraseña.
    monkeypatch.setenv("POSTGRES_APP_USER", contenedor.username)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", contenedor.password)
    monkeypatch.setenv("POSTGRES_DB", contenedor.dbname)
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("REDIS_PORT", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "x")
    ruta_parametros = tmp_path / "parametros.yaml"
    ruta_parametros.write_text((RAIZ_BACKEND.parent / "config" / "parametros.yaml").read_text())
    monkeypatch.setenv("PROPTECH_PARAMETROS", str(ruta_parametros))

    from proptech_api.app import crear_app

    # `crear_app()` llama `configurar_logs("api")` DE NUEVO adentro, y cada
    # llamada reemplaza los handlers (los vacía antes de poner el suyo, para
    # no duplicar líneas si el proceso reconfigura los logs): capturar la
    # salida ANTES de `crear_app()` apunta al handler viejo, que `crear_app()`
    # tira. Por eso se captura DESPUÉS de crearla, y antes de que el
    # `lifespan` (que corre recién al entrar al `TestClient`) escriba nada.
    app = crear_app()
    salida = _capturar_logs_json()
    with pytest.raises(RolDeAplicacionInseguro), TestClient(app):
        pass

    eventos = _eventos_json(salida.getvalue())
    fallidos = [e for e in eventos if e.get("evento") == "arranque_fallido"]
    assert len(fallidos) == 1, f"salida completa: {salida.getvalue()!r}"
    assert "superusuario" in fallidos[0].get("causa", "")
    assert contenedor.password not in salida.getvalue()


@pytest.mark.anyio
async def test_worker_logea_arranque_fallido_si_el_rol_es_inseguro(
    contenedor: PostgresContainer,
    esquema: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    ajustes_del_worker: object,
) -> None:
    """Gemelo del test de la API (L-009). Depende de `ajustes_del_worker`
    (conftest) por la misma razón que `test_cableado_real_del_arranque.py`:
    forzar que el primer import de `proptech_worker.ajustes` en la sesión
    pase por el entorno correcto del contenedor de sesión."""
    from proptech_core.compartido.configuracion import Configuracion

    ruta_parametros = tmp_path / "parametros.yaml"
    ruta_parametros.write_text((RAIZ_BACKEND.parent / "config" / "parametros.yaml").read_text())
    entorno = {
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_APP_USER": contenedor.username,
        "POSTGRES_APP_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PORT": "1",
        "REDIS_PASSWORD": "x",
        "PROPTECH_PARAMETROS": str(ruta_parametros),
    }
    for clave, valor in entorno.items():
        monkeypatch.setenv(clave, valor)
    configuracion_insegura = Configuracion()

    import proptech_worker.ajustes as ajustes_mod

    monkeypatch.setattr(ajustes_mod, "_configuracion", configuracion_insegura)
    salida = _capturar_logs_json()

    ctx: dict[str, Any] = {}
    with pytest.raises(RolDeAplicacionInseguro):
        await ajustes_mod.on_startup(ctx)

    eventos = _eventos_json(salida.getvalue())
    fallidos = [e for e in eventos if e.get("evento") == "arranque_fallido"]
    assert len(fallidos) == 1, f"salida completa: {salida.getvalue()!r}"
    assert "superusuario" in fallidos[0].get("causa", "")
    assert contenedor.password not in salida.getvalue()
