"""Tests de `datos_de_excepcion` y de `configurar_logs(servicio)` (D7, D13).

Escenarios de `trazabilidad-y-logs`: Error de un tercero con datos en su mensaje;
Mensaje con argumentos. Cambio 1c, tarea 2.2. Lecciones: L-007 (el mensaje de una
excepción de terceros, incluido psycopg, no debe llegar a la salida).
"""

import io
import json
import logging
from collections.abc import Iterator

import psycopg
import pytest

from proptech_core.compartido.logs import FormateadorJSON, configurar_logs, datos_de_excepcion

_LOGGERS_RECABLEADOS = ["", "uvicorn", "uvicorn.error", "arq"]


@pytest.fixture
def _logging_restaurado() -> Iterator[None]:
    """Guarda y restaura los handlers y el nivel de los loggers que toca
    `configurar_logs`, para no dejar estado global pisado entre tests."""
    originales = {
        nombre: (logging.getLogger(nombre).handlers[:], logging.getLogger(nombre).level)
        for nombre in _LOGGERS_RECABLEADOS
    }
    try:
        yield
    finally:
        for nombre, (handlers, nivel) in originales.items():
            logger = logging.getLogger(nombre)
            logger.handlers[:] = handlers
            logger.setLevel(nivel)


def _funcion_que_falla_marcada(marcador: str) -> None:
    raise ValueError(f"{marcador}: detalle que no debería salir")


def test_tipo_error_es_el_nombre_calificado() -> None:
    try:
        _funcion_que_falla_marcada("sin-usar")
    except ValueError as error:
        datos = datos_de_excepcion(error)
    assert datos["tipo_error"] == "builtins.ValueError"


def test_traza_tiene_cuadros_modulo_linea_funcion_sin_mensaje_ni_codigo() -> None:
    marcador = "marcador-mensaje-9f3e"
    try:
        _funcion_que_falla_marcada(marcador)
    except ValueError as error:
        datos = datos_de_excepcion(error)

    traza = datos["traza"]
    assert isinstance(traza, list)
    assert len(traza) >= 1
    assert all(isinstance(cuadro, str) for cuadro in traza)
    assert any("_funcion_que_falla_marcada" in cuadro for cuadro in traza)
    # Ni el mensaje de la excepción ni el texto de la línea de código fuente
    # ("raise ValueError(...)") aparecen en ningún cuadro.
    serializado = json.dumps(datos)
    assert marcador not in serializado
    assert "raise ValueError" not in serializado


def _raiz_de_recursion(profundidad: int, marcador: str) -> None:
    if profundidad == 0:
        raise RuntimeError(f"{marcador}: fondo de la recursión")
    _raiz_de_recursion(profundidad - 1, marcador)


def test_traza_se_recorta_a_10_cuadros() -> None:
    try:
        _raiz_de_recursion(20, "marcador-profundo")
    except RuntimeError as error:
        datos = datos_de_excepcion(error)
    traza = datos["traza"]
    assert isinstance(traza, list)
    assert len(traza) == 10


def test_marcador_de_psycopg_operational_error_no_aparece_en_la_salida() -> None:
    marcador = "host-secreto-10.0.0.55"
    try:
        raise psycopg.OperationalError(f"no se pudo conectar a {marcador}")
    except psycopg.OperationalError as error:
        datos = datos_de_excepcion(error)
    assert marcador not in json.dumps(datos)
    tipo_error = datos["tipo_error"]
    assert isinstance(tipo_error, str)
    assert tipo_error.endswith("OperationalError")


def test_configurar_logs_reemplaza_los_handlers_de_los_cuatro_loggers(
    _logging_restaurado: None,
) -> None:
    configurar_logs("api")
    for nombre in _LOGGERS_RECABLEADOS:
        logger = logging.getLogger(nombre)
        assert len(logger.handlers) == 1, f"{nombre!r} no tiene exactamente un handler"
        assert isinstance(logger.handlers[0].formatter, FormateadorJSON)


def test_llamar_configurar_logs_dos_veces_no_duplica_lineas(_logging_restaurado: None) -> None:
    configurar_logs("api")
    configurar_logs("api")

    salida = io.StringIO()
    logger_raiz = logging.getLogger()
    for handler in logger_raiz.handlers:
        handler.stream = salida  # type: ignore[attr-defined]

    logger_raiz.warning("evento_unico_de_prueba")

    lineas = [linea for linea in salida.getvalue().splitlines() if linea.strip()]
    assert len(lineas) == 1


def test_log_de_arq_con_argumentos_sale_como_plantilla(_logging_restaurado: None) -> None:
    configurar_logs("worker")

    salida = io.StringIO()
    logger_arq = logging.getLogger("arq")
    for handler in logger_arq.handlers:
        handler.stream = salida  # type: ignore[attr-defined]

    logger_arq.info("tarea %s ejecutada con %s", "tarea_de_prueba", "dato-secreto-arq")

    linea = salida.getvalue().strip()
    datos = json.loads(linea)
    assert datos["evento"] == "tarea %s ejecutada con %s"
    assert "dato-secreto-arq" not in linea
