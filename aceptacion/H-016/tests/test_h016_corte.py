"""Aceptación de H-016 · corte del lado de la base para las tareas del worker (F2c, D-158).

Caja negra sobre `proptech_worker.corte.ejecutar_con_corte` contra PostgreSQL real (testcontainers), con
la base migrada como en `tests/integracion/test_idempotencia.py`. La "base trabada" se simula con otra
transacción que reserva la misma clave sin confirmar: el `INSERT` de la tarea queda esperando el candado.
"""

from __future__ import annotations

import importlib
import inspect
import subprocess
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from .._edificios import BaseDeEdificio

RAIZ_BACKEND = Path(__file__).resolve().parents[3]
TAREA = "tarea_de_prueba"

pytestmark = pytest.mark.integracion


@pytest.fixture
def fabrica(base_para_migraciones: BaseDeEdificio, monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    from proptech_core.compartido.base_de_datos import crear_engine, crear_fabrica_de_sesiones
    from proptech_core.compartido.configuracion import Configuracion

    from ...conftest import APP_PASSWORD_DE_SESION, APP_USER_DE_SESION

    entorno = dict(base_para_migraciones.entorno)
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=RAIZ_BACKEND, env=entorno, check=True,
                   capture_output=True, text=True)
    for clave, valor in entorno.items():
        if clave.startswith("POSTGRES_"):
            monkeypatch.setenv(clave, valor)
    monkeypatch.setenv("POSTGRES_APP_USER", APP_USER_DE_SESION)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", APP_PASSWORD_DE_SESION)
    engine = crear_engine(Configuracion())
    try:
        yield crear_fabrica_de_sesiones(engine)
    finally:
        engine.dispose()
        subprocess.run(["uv", "run", "alembic", "downgrade", "base"], cwd=RAIZ_BACKEND, env=entorno,
                       check=True, capture_output=True, text=True)


def _modulo() -> Any:
    try:
        return importlib.import_module("proptech_worker.corte")
    except ImportError as error:
        raise AssertionError(f"falta `proptech_worker.corte` (H-016): {error}") from None


def _ejecutar(fabrica: sessionmaker[Session], clave: str, efecto: Any, cota_s: float = 0.5) -> bool:
    funcion = getattr(_modulo(), "ejecutar_con_corte", None)
    assert funcion is not None, "falta `ejecutar_con_corte`"
    return bool(funcion(fabrica, administracion_id=None, cota_s=cota_s, clave=clave, tarea=TAREA,
                        request_id=str(uuid.uuid4()), efecto=efecto))


def _corte() -> type[BaseException]:
    clase = getattr(_modulo(), "CorteDeLaBase", None)
    assert clase is not None, "falta `CorteDeLaBase`"
    from proptech_core.compartido.reintentos import ErrorPasajero

    assert issubclass(clase, ErrorPasajero), "`CorteDeLaBase` tiene que ser un `ErrorPasajero` (se reintenta)"
    return clase


def _filas(fabrica: sessionmaker[Session], clave: str) -> int:
    with fabrica() as sesion:
        return int(sesion.execute(text("SELECT count(*) FROM trabajos_hechos WHERE clave = :c"), {"c": clave}).scalar_one())


def test_c01_la_sesion_lleva_la_cota_de_la_tarea(fabrica: sessionmaker[Session]) -> None:
    vistos: dict[str, str] = {}

    def efecto(sesion: Session) -> None:
        for nombre in ("statement_timeout", "lock_timeout", "idle_in_transaction_session_timeout"):
            vistos[nombre] = str(sesion.execute(text(f"SHOW {nombre}")).scalar_one())

    assert _ejecutar(fabrica, f"c01-{uuid.uuid4()}", efecto) is True
    assert vistos == {"statement_timeout": "500ms", "lock_timeout": "500ms",
                      "idle_in_transaction_session_timeout": "500ms"}, vistos
    with fabrica() as sesion:
        assert str(sesion.execute(text("SHOW statement_timeout")).scalar_one()) != "500ms", (
            "la cota tiene que ser local a la transacción de la tarea"
        )


def test_c02_c03_trabada_se_corta_y_el_reintento_confirma_una_vez(fabrica: sessionmaker[Session]) -> None:
    corte = _corte()
    clave = f"c02-{uuid.uuid4()}"
    bloqueo = fabrica()
    bloqueo.execute(text("INSERT INTO trabajos_hechos (clave, tarea, request_id) VALUES (:c, :t, :r)"),
                    {"c": clave, "t": TAREA, "r": str(uuid.uuid4())})
    resultado: dict[str, Any] = {}

    def correr() -> None:
        inicio = time.monotonic()
        try:
            resultado["valor"] = _ejecutar(fabrica, clave, lambda _s: None)
        except BaseException as error:  # noqa: BLE001
            resultado["error"] = error
        resultado["segundos"] = time.monotonic() - inicio

    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()
    hilo.join(timeout=10)
    assert not hilo.is_alive(), "la tarea sigue esperando: no hay corte del lado de la base"
    bloqueo.rollback()
    bloqueo.close()
    assert isinstance(resultado.get("error"), corte), f"se esperaba CorteDeLaBase: {resultado}"
    assert resultado["segundos"] < 3, f"tardó {resultado['segundos']:.1f} s en cortarse"
    time.sleep(1)
    assert _filas(fabrica, clave) == 0, "liberada la base, la tarea cortada confirmó igual"
    corridas: list[int] = []
    assert _ejecutar(fabrica, clave, lambda _s: corridas.append(1)) is True
    assert _ejecutar(fabrica, clave, lambda _s: corridas.append(1)) is False
    assert corridas == [1] and _filas(fabrica, clave) == 1


def test_c04_la_tarea_de_prueba_pasa_por_el_corte() -> None:
    tareas = importlib.import_module("proptech_worker.tareas")
    assert not hasattr(tareas, "COTA_OPERACION_S"), "la cota genérica del 1c tiene que desaparecer"
    assert "ejecutar_con_corte" in inspect.getsource(tareas), "la tarea de prueba no usa `ejecutar_con_corte`"


def test_n01_un_efecto_lento_no_confirma(fabrica: sessionmaker[Session]) -> None:
    corte = _corte()
    clave = f"n01-{uuid.uuid4()}"
    with pytest.raises(corte):
        _ejecutar(fabrica, clave, lambda s: s.execute(text("SELECT pg_sleep(1.5)")))
    assert _filas(fabrica, clave) == 0


def test_n02_un_efecto_que_termina_tarde_no_confirma(fabrica: sessionmaker[Session]) -> None:
    corte = _corte()
    clave = f"n02-{uuid.uuid4()}"
    with pytest.raises(corte):
        _ejecutar(fabrica, clave, lambda _s: time.sleep(0.8))
    assert _filas(fabrica, clave) == 0
