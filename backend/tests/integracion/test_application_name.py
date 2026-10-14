"""Tests de integración: el `application_name` de la sesión lleva el
`request_id` sólo dentro de su transacción (D7, D8). Cambio 1c, tarea 3.4.

Escenario de `trazabilidad-y-logs`: En la sesión de la base. Usa un
contenedor propio (no el de sesión de `conftest.py`): necesita el
`log_line_prefix` de D7, que el contenedor compartido no tiene.
"""

import time
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.base_de_datos import (
    crear_fabrica_de_sesiones,
    registrar_application_name,
)
from proptech_core.compartido.seguimiento import request_id_actual

from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

pytestmark = pytest.mark.integracion

LOG_LINE_PREFIX = "%m [%p] %q%a "


@pytest.fixture
def contenedor_con_log_line_prefix() -> Iterator[PostgresContainer]:
    contenedor = PostgresContainer(IMAGEN_POSTGRES_PARA_TESTS, driver="psycopg")
    contenedor.with_command(["postgres", "-c", f"log_line_prefix={LOG_LINE_PREFIX}"])
    with contenedor as iniciado:
        yield iniciado


def _engine(contenedor: PostgresContainer) -> Engine:
    return create_engine(
        contenedor.get_connection_url(), connect_args={"application_name": "proptech-api"}
    )


def test_application_name_lleva_el_request_id_solo_dentro_de_la_transaccion(
    contenedor_con_log_line_prefix: PostgresContainer,
) -> None:
    engine = _engine(contenedor_con_log_line_prefix)
    try:
        fabrica = crear_fabrica_de_sesiones(engine)
        registrar_application_name(fabrica, "proptech-api")

        request_id = "3f2c1a00-aaaa-4000-8000-000000000001"
        token = request_id_actual.set(request_id)
        try:
            sesion = fabrica()
            try:
                valor = sesion.execute(
                    text("SELECT current_setting('application_name')")
                ).scalar_one()
                assert request_id in valor
            finally:
                sesion.close()
        finally:
            request_id_actual.reset(token)

        # Fuera del pedido (ContextVar en None otra vez): la transacción
        # siguiente de la MISMA conexión ya no lo lleva, vuelve al nombre
        # base fijado en `connect_args`.
        sesion_siguiente = fabrica()
        try:
            valor_siguiente = sesion_siguiente.execute(
                text("SELECT current_setting('application_name')")
            ).scalar_one()
            assert request_id not in valor_siguiente
            assert valor_siguiente == "proptech-api"
        finally:
            sesion_siguiente.close()
    finally:
        engine.dispose()


def test_un_error_provocado_deja_el_request_id_en_los_logs_del_contenedor(
    contenedor_con_log_line_prefix: PostgresContainer,
) -> None:
    engine = _engine(contenedor_con_log_line_prefix)
    try:
        fabrica = crear_fabrica_de_sesiones(engine)
        registrar_application_name(fabrica, "proptech-api")

        request_id = "3f2c1a00-bbbb-4000-8000-000000000002"
        token = request_id_actual.set(request_id)
        try:
            sesion = fabrica()
            try:
                with pytest.raises(Exception, match="division by zero"):
                    sesion.execute(text("SELECT 1/0"))
                sesion.rollback()
            finally:
                sesion.close()
        finally:
            request_id_actual.reset(token)
    finally:
        engine.dispose()

    # Los logs del contenedor pueden tardar un instante en aparecer.
    texto_logs = ""
    for _ in range(20):
        salida_stdout, salida_stderr = contenedor_con_log_line_prefix.get_logs()
        texto_logs = salida_stdout.decode("utf-8", errors="replace") + salida_stderr.decode(
            "utf-8", errors="replace"
        )
        if request_id in texto_logs:
            break
        time.sleep(0.25)

    assert request_id in texto_logs, texto_logs[-2000:]
