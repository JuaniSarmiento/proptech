"""Buscar un valor rechazado en TODO el log (C2V2-2, N-b del cambio 2e `humo-y-ci`).

`capturar_todo` baja el logger raíz a `DEBUG` mientras dura el bloque, así un registro de cualquier
severidad y de cualquier logger llega a `caplog`. `fugas_del_valor` mira el mensaje y cada campo
extra de cada registro por VALOR (una hoja que es el valor, o un texto donde aparece como palabra
aparte), no con `valor in str(campos)`: ese chequeo daba rojo falso cuando un número ajeno
(`1230`, `a1234`, `created`, un id de hilo) contenía por azar los mismos dígitos.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from proptech_core.compartido.logs import _ATRIBUTOS_ESTANDAR


@contextmanager
def capturar_todo(caplog: pytest.LogCaptureFixture) -> Iterator[None]:
    raiz = logging.getLogger()
    severidad_anterior = raiz.level
    caplog.set_level(logging.DEBUG)
    # `configurar_logs` deja `arq`, `uvicorn` y `uvicorn.error` con `propagate=False`: sus registros
    # no llegan a la raíz y `caplog` no los vería. Se les engancha su manejador mientras dure.
    enganchados = [
        logger
        for logger in logging.Logger.manager.loggerDict.values()
        if isinstance(logger, logging.Logger) and not logger.propagate
    ]
    for logger in enganchados:
        logger.addHandler(caplog.handler)
    try:
        yield
    finally:
        for logger in enganchados:
            logger.removeHandler(caplog.handler)
        raiz.setLevel(severidad_anterior)


def _hojas(valor: Any) -> Iterator[Any]:
    if isinstance(valor, dict):
        for clave, contenido in valor.items():
            yield from _hojas(clave)
            yield from _hojas(contenido)
    elif isinstance(valor, list | tuple | set | frozenset):
        for contenido in valor:
            yield from _hojas(contenido)
    else:
        yield valor


def _aparece(hoja: Any, valor: Any, patron: re.Pattern[str]) -> bool:
    if hoja == valor and type(hoja) is type(valor):
        return True
    if isinstance(hoja, str):
        return patron.search(hoja) is not None
    return str(hoja) == str(valor)


def fugas_del_valor(registros: list[logging.LogRecord], valor: Any) -> list[str]:
    """Dónde aparece `valor` en `registros`: una descripción por cada aparición."""
    texto = str(valor)
    # Palabra aparte: ni pegada a otra letra o dígito, ni parte de un número con decimales o de una
    # ruta (`123.5`, `a.123`); un punto de fin de oración (`... no-es-uuid.`) sí cuenta como borde.
    patron = re.compile(rf"(?<![\w.]){re.escape(texto)}(?!\w|\.\w)")
    fugas = []
    for registro in registros:
        if patron.search(registro.getMessage()):
            fugas.append(f"{registro.name}: mensaje {registro.getMessage()!r}")
        for campo, contenido in registro.__dict__.items():
            if campo in _ATRIBUTOS_ESTANDAR:
                continue
            if any(_aparece(hoja, valor, patron) for hoja in _hojas(contenido)):
                fugas.append(f"{registro.name}: campo {campo!r} = {contenido!r}")
    return fugas
