"""Tests de integración de `ejecutar_una_vez` contra PostgreSQL real (D3).
Cambio 1c, tarea 5.2.

Escenarios de `cola-de-trabajos`: Trabajo ejecutado dos veces; Dos ejecuciones
simultáneas; El efecto falla después de reservar la clave.
"""

import subprocess
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import crear_engine, crear_fabrica_de_sesiones
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.idempotencia import ejecutar_una_vez

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integracion


def _alembic_env(contenedor: PostgresContainer) -> dict[str, str]:
    import os

    entorno = {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        # Alembic corre como el migrador (D1, D2, cambio 2a).
        "POSTGRES_MIGRADOR_USER": contenedor.username,
        "POSTGRES_MIGRADOR_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
    }
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


@pytest.fixture
def fabrica(
    postgres_contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sessionmaker[Session]]:
    """Migra a `head`, entrega una fábrica de sesiones y, al terminar,
    vuelve a `base` para no dejarle estado a otros tests del mismo
    contenedor de sesión (L-006)."""
    env = _alembic_env(postgres_contenedor)
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    for clave, valor in env.items():
        if clave.startswith("POSTGRES_"):
            monkeypatch.setenv(clave, valor)
    # `Configuracion` (la que usa `crear_engine` abajo) lee el par de la app
    # (D3): antes del 2.2 es el mismo usuario del contenedor que el migrador.
    monkeypatch.setenv("POSTGRES_APP_USER", postgres_contenedor.username)
    monkeypatch.setenv("POSTGRES_APP_PASSWORD", postgres_contenedor.password)
    engine = crear_engine(Configuracion())
    try:
        yield crear_fabrica_de_sesiones(engine)
    finally:
        engine.dispose()
        subprocess.run(
            ["uv", "run", "alembic", "downgrade", "base"],
            cwd=RAIZ_BACKEND,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )


def _tarea_registrada(fabrica: sessionmaker[Session], clave: str) -> bool:
    with fabrica() as sesion:
        fila = sesion.execute(
            text("SELECT 1 FROM trabajos_hechos WHERE clave = :clave"), {"clave": clave}
        ).first()
        return fila is not None


def test_primera_ejecucion_corre_el_efecto_y_registra_la_clave(
    fabrica: sessionmaker[Session],
) -> None:
    clave = f"idem-{uuid.uuid4()}"
    request_id = str(uuid.uuid4())
    corridas = []

    with fabrica() as sesion:
        resultado = ejecutar_una_vez(
            sesion,
            clave=clave,
            tarea="tarea_de_prueba",
            request_id=request_id,
            efecto=lambda s: corridas.append(1),
        )
    assert resultado is True
    assert corridas == [1]

    with fabrica() as sesion:
        fila = sesion.execute(
            text("SELECT request_id FROM trabajos_hechos WHERE clave = :clave"),
            {"clave": clave},
        ).first()
    assert fila is not None
    assert str(fila[0]) == request_id


def test_segunda_ejecucion_devuelve_false_sin_correr_el_efecto(
    fabrica: sessionmaker[Session],
) -> None:
    clave = f"idem-{uuid.uuid4()}"
    corridas = []

    with fabrica() as sesion:
        ejecutar_una_vez(
            sesion,
            clave=clave,
            tarea="tarea_de_prueba",
            request_id=str(uuid.uuid4()),
            efecto=lambda s: corridas.append(1),
        )

    with fabrica() as sesion:
        resultado = ejecutar_una_vez(
            sesion,
            clave=clave,
            tarea="tarea_de_prueba",
            request_id=str(uuid.uuid4()),
            efecto=lambda s: corridas.append(2),
        )
    assert resultado is False
    assert corridas == [1]


def test_si_el_efecto_lanza_no_queda_la_clave_y_un_segundo_intento_completa(
    fabrica: sessionmaker[Session],
) -> None:
    clave = f"idem-{uuid.uuid4()}"

    def _efecto_que_falla(sesion: Session) -> None:
        raise ValueError("falla a propósito")

    with fabrica() as sesion, pytest.raises(ValueError):
        ejecutar_una_vez(
            sesion,
            clave=clave,
            tarea="tarea_de_prueba",
            request_id=str(uuid.uuid4()),
            efecto=_efecto_que_falla,
        )
    assert _tarea_registrada(fabrica, clave) is False

    corridas = []
    with fabrica() as sesion:
        resultado = ejecutar_una_vez(
            sesion,
            clave=clave,
            tarea="tarea_de_prueba",
            request_id=str(uuid.uuid4()),
            efecto=lambda s: corridas.append(1),
        )
    assert resultado is True
    assert corridas == [1]
    assert _tarea_registrada(fabrica, clave) is True


def test_dos_ejecuciones_simultaneas_el_efecto_corre_una_sola_vez(
    fabrica: sessionmaker[Session],
) -> None:
    clave = f"idem-{uuid.uuid4()}"
    resultados: list[bool] = []
    corridas: list[int] = []
    lock = threading.Lock()

    def _correr() -> None:
        with fabrica() as sesion:
            resultado = ejecutar_una_vez(
                sesion,
                clave=clave,
                tarea="tarea_de_prueba",
                request_id=str(uuid.uuid4()),
                efecto=lambda s: corridas.append(1),
            )
        with lock:
            resultados.append(resultado)

    hilos = [threading.Thread(target=_correr) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert sorted(resultados) == [False, True]
    assert corridas == [1]
