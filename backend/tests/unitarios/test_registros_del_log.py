"""El helper que busca un valor rechazado en el log (C2V2-2, N-b del cambio 2e `humo-y-ci`).

Los dos defectos del test viejo de `test_worker_tenant.py`: un `WARNING` con el valor en OTRO logger
pasaba desapercibido (sólo se capturaba `ERROR` de un logger), y un campo que contuviera "123" por
azar (`1230`, `a1234`) daba rojo falso con `valor=123`.
"""

from __future__ import annotations

import logging

import pytest

from tests._registros_del_log import capturar_todo, fugas_del_valor


def test_un_warning_con_el_valor_en_otro_logger_se_ve(caplog: pytest.LogCaptureFixture) -> None:
    with capturar_todo(caplog):
        logging.getLogger("otro.modulo").warning("administracion rara", extra={"dato": 123})
    assert fugas_del_valor(caplog.records, 123) != []


def test_un_info_en_un_logger_hijo_con_el_valor_en_el_mensaje_se_ve(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with capturar_todo(caplog):
        logging.getLogger("a.b.c").info("recibí valor=123 y seguí")
    assert fugas_del_valor(caplog.records, 123) != []


def test_un_campo_que_contiene_123_por_azar_no_es_una_fuga(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with capturar_todo(caplog):
        logging.getLogger("otro.modulo").error(
            "tarea_sin_administracion",
            extra={"tarea": "a1234", "intentos": 1230, "ids": ["x123y", 4123]},
        )
    assert fugas_del_valor(caplog.records, 123) == []


def test_el_valor_dentro_de_una_lista_o_un_diccionario_extra_se_ve(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with capturar_todo(caplog):
        logging.getLogger("x").error("m", extra={"detalle": {"recibido": ["123"]}})
    assert fugas_del_valor(caplog.records, 123) != []


def test_capturar_todo_restaura_la_severidad_del_logger_raiz(
    caplog: pytest.LogCaptureFixture,
) -> None:
    antes = logging.getLogger().level
    with capturar_todo(caplog):
        assert logging.getLogger().level == logging.DEBUG
    assert logging.getLogger().level == antes
