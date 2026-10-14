"""Ataque vuelta 2 (F7): el arreglo saca `tipo_error` de la ÚLTIMA línea del
traceback crudo. Si el mensaje de la excepción tiene varias líneas (psycopg y
SQLAlchemy las tienen: "Is the server running...", "(Background on this
error...)"), esa última línea es parte del MENSAJE, no el tipo. Tampoco cubre
un `logger.error(exc)` de uvicorn (el objeto excepción como `msg`)."""

import io
import json
import logging
import traceback

import pytest

from proptech_core.compartido.logs import FormateadorJSON

MARCADOR = "marcador-tb-v2-91ac"


def _formatear(msg: object) -> str:
    salida = io.StringIO()
    handler = logging.StreamHandler(salida)
    handler.setFormatter(FormateadorJSON(servicio="api"))
    logger = logging.getLogger("uvicorn.error.prueba_rompedor")
    logger.handlers = [handler]
    logger.propagate = False
    logger.error(msg)
    return salida.getvalue()


@pytest.mark.parametrize(
    "mensaje_de_la_excepcion",
    [
        f"connection failed\nuser {MARCADOR}",
        f"connection failed: FATAL\n\tIs the server running on host {MARCADOR}?",
        f"primera linea\n{MARCADOR}: segunda",
    ],
)
def test_traceback_crudo_con_mensaje_multilinea_no_deja_el_mensaje(
    mensaje_de_la_excepcion: str,
) -> None:
    try:
        raise RuntimeError(mensaje_de_la_excepcion)
    except RuntimeError:
        crudo = traceback.format_exc()  # lo que Starlette manda en startup.failed
    linea = _formatear(crudo)
    assert json.loads(linea)["evento"] == "traceback_crudo_descartado"
    assert MARCADOR not in linea


def test_un_objeto_excepcion_como_msg_no_deja_su_mensaje() -> None:
    # uvicorn/server.py:190 y uvicorn/config.py:578,605 hacen logger.error(exc)
    linea = _formatear(OSError(98, f"address already in use {MARCADOR}"))
    assert MARCADOR not in linea
