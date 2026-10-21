"""Test de integración de la migración `0002` (D3). Cambio 1c, tarea 5.1.

Ida y vuelta sobre base vacía: la tabla `trabajos_hechos` con sus columnas, su
PK y el `CHECK` del largo de la clave (vacía y de 201 caracteres rechazadas).

Además, en el mismo proceso: llamar a `configurar_logs`, correr
`alembic upgrade head` (vía la API de Alembic, no un subproceso, para que la
migración corra en el mismo proceso de pytest) y afirmar que un logger ya
configurado por `configurar_logs` (D7) no queda deshabilitado ni pierde su
línea JSON — hoy `fileConfig` de `migraciones/env.py` corre con
`disable_existing_loggers=True` y lo apaga (M16).

Escenarios de `cola-de-trabajos`: Trabajo ejecutado dos veces (la unicidad que
lo sostiene). Escenarios de `integracion-continua`: Migraciones en el CI.
Escenarios de `trazabilidad-y-logs`: Las migraciones no apagan los logs.
"""

import io
import json
import logging
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import text

from ._edificios import BaseDeEdificio

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integracion


@pytest.fixture
def _logging_restaurado() -> Iterator[None]:
    loggers = [logging.getLogger()] + [
        logger
        for logger in logging.Logger.manager.loggerDict.values()
        if isinstance(logger, logging.Logger)
    ]
    originales = [
        (
            logger,
            logger.handlers[:],
            logger.filters[:],
            logger.level,
            logger.propagate,
            logger.disabled,
        )
        for logger in loggers
    ]
    try:
        yield
    finally:
        for logger, handlers, filtros, nivel, propaga, deshabilitado in originales:
            logger.handlers[:] = handlers
            logger.filters[:] = filtros
            logger.setLevel(nivel)
            logger.propagate = propaga
            logger.disabled = deshabilitado


def _alembic_env(base: BaseDeEdificio) -> dict[str, str]:
    entorno = dict(base.entorno)
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _engine_directo(base: BaseDeEdificio) -> sa.Engine:
    contenedor = base.contenedor
    url = (
        f"postgresql+psycopg://{contenedor.username}:{contenedor.password}"
        f"@{contenedor.get_container_host_ip()}:{contenedor.get_exposed_port(5432)}"
        f"/{base.nombre}"
    )
    return sa.create_engine(url)


def test_upgrade_head_crea_trabajos_hechos_y_downgrade_la_borra(
    base_para_migraciones: BaseDeEdificio,
) -> None:
    env = _alembic_env(base_para_migraciones)
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        engine = _engine_directo(base_para_migraciones)
        with engine.connect() as conexion:
            columnas = {
                fila[0]: fila[1]
                for fila in conexion.execute(
                    text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = 'trabajos_hechos'"
                    )
                )
            }
            assert columnas == {
                "clave": "text",
                "tarea": "text",
                "request_id": "uuid",
                "hecho_en": "timestamp with time zone",
            }

            # PK sobre `clave`.
            conexion.execute(
                text(
                    "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
                    "VALUES ('k1', 'tarea_de_prueba', gen_random_uuid())"
                )
            )
            with pytest.raises(sa.exc.IntegrityError):
                conexion.execute(
                    text(
                        "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
                        "VALUES ('k1', 'tarea_de_prueba', gen_random_uuid())"
                    )
                )
            conexion.rollback()

            # CHECK del largo de la clave: vacía (0) y 201 caracteres, rechazadas.
            with pytest.raises(sa.exc.IntegrityError):
                conexion.execute(
                    text(
                        "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
                        "VALUES ('', 'tarea_de_prueba', gen_random_uuid())"
                    )
                )
            conexion.rollback()

            with pytest.raises(sa.exc.IntegrityError):
                conexion.execute(
                    text(
                        "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
                        "VALUES (:clave, 'tarea_de_prueba', gen_random_uuid())"
                    ),
                    {"clave": "k" * 201},
                )
            conexion.rollback()

            # 200 caracteres: el límite aceptado.
            conexion.execute(
                text(
                    "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
                    "VALUES (:clave, 'tarea_de_prueba', gen_random_uuid())"
                ),
                {"clave": "k" * 200},
            )
            conexion.commit()
        engine.dispose()
    finally:
        subprocess.run(
            ["uv", "run", "alembic", "downgrade", "base"],
            cwd=RAIZ_BACKEND,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    engine = _engine_directo(base_para_migraciones)
    with engine.connect() as conexion:
        existe = conexion.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'trabajos_hechos')"
            )
        ).scalar()
        assert existe is False
    engine.dispose()


def test_migrar_en_el_mismo_proceso_no_deshabilita_un_logger_ya_configurado(
    base_para_migraciones: BaseDeEdificio,
    monkeypatch: pytest.MonkeyPatch,
    _logging_restaurado: None,
) -> None:
    from proptech_core.compartido.logs import configurar_logs

    env = _alembic_env(base_para_migraciones)
    for clave, valor in env.items():
        if clave.startswith("POSTGRES_"):
            monkeypatch.setenv(clave, valor)

    configurar_logs("test")
    logger_arq = logging.getLogger("arq")
    salida = io.StringIO()
    for handler in logger_arq.handlers:
        handler.stream = salida  # type: ignore[attr-defined]

    assert logger_arq.disabled is False

    from alembic import command
    from alembic.config import Config

    config = Config(str(RAIZ_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ_BACKEND / "migraciones"))
    try:
        command.upgrade(config, "head")

        assert logger_arq.disabled is False, (
            "fileConfig de migraciones/env.py deshabilitó un logger ya configurado "
            "(disable_existing_loggers=True lo apaga en silencio)"
        )

        logger_arq.info("evento_tras_migrar")
        linea = salida.getvalue().strip().splitlines()[-1]
        datos = json.loads(linea)
        assert datos["evento"] == "evento_tras_migrar"
    finally:
        command.downgrade(config, "base")
