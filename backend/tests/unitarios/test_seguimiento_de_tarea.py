"""Tests del decorador que hace viajar el `request_id` dentro de una tarea
del worker (D8). Cambio 1c, tarea 5.5.

El decorador fija la `ContextVar` con el argumento antes de correr la tarea
y la limpia al terminar; si el argumento falta o es inválido, genera uno
nuevo y loguea `request_id_reemplazado`.
"""

from typing import Any

import pytest

from proptech_core.compartido.seguimiento import (
    con_seguimiento_de_tarea,
    request_id_actual,
    validar_request_id,
)

pytestmark = pytest.mark.anyio


async def test_el_request_id_valido_queda_en_la_contextvar_durante_la_tarea() -> None:
    vistos = []

    @con_seguimiento_de_tarea
    async def tarea(ctx: dict[str, Any], *, request_id: str) -> None:
        vistos.append(request_id_actual.get())

    request_id = "3f2c1a00-aaaa-4000-8000-000000000001"
    await tarea({}, request_id=request_id)

    assert vistos == [request_id]
    assert request_id_actual.get() is None  # limpiada al terminar


async def test_un_request_id_invalido_se_reemplaza_y_se_loguea(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    vistos = []

    @con_seguimiento_de_tarea
    async def tarea(ctx: dict[str, Any], *, request_id: str) -> None:
        vistos.append(request_id)

    await tarea({}, request_id="no-es-un-uuid")

    assert len(vistos) == 1
    assert validar_request_id(vistos[0]) == vistos[0]  # se reemplazó por uno válido
    assert any(r.msg == "request_id_reemplazado" for r in caplog.records)


async def test_la_contextvar_se_limpia_incluso_si_la_tarea_lanza() -> None:
    @con_seguimiento_de_tarea
    async def tarea(ctx: dict[str, Any], *, request_id: str) -> None:
        raise ValueError("falla a propósito")

    with pytest.raises(ValueError):
        await tarea({}, request_id="3f2c1a00-aaaa-4000-8000-000000000002")

    assert request_id_actual.get() is None


async def test_un_request_id_faltante_se_reemplaza_y_se_loguea(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ataque del rompedor (vuelta 2, F5; D8): un trabajo armado a mano (o
    encolado por código que se olvidó el argumento) llega SIN `request_id`.
    El decorador lo exigía como argumento obligatorio sin default: Python
    levantaba `TypeError` antes de que el cuerpo del decorador pudiera
    reemplazarlo, en vez de generar uno nuevo y loguear
    `request_id_reemplazado` como con un valor inválido."""
    caplog.set_level("INFO")
    vistos: list[str] = []

    @con_seguimiento_de_tarea
    async def tarea(ctx: dict[str, Any], *, request_id: str) -> None:
        vistos.append(request_id)

    await tarea({})  # sin request_id: como un trabajo armado a mano en Redis

    assert len(vistos) == 1
    assert validar_request_id(vistos[0]) == vistos[0]
    assert any(r.msg == "request_id_reemplazado" for r in caplog.records)


async def test_un_request_id_no_texto_se_reemplaza() -> None:
    """Triangula el caso anterior con un segundo tipo de entrada inválida:
    un `request_id` que no es texto (por ejemplo, un número en un trabajo
    armado a mano)."""
    vistos: list[str] = []

    @con_seguimiento_de_tarea
    async def tarea(ctx: dict[str, Any], *, request_id: str) -> None:
        vistos.append(request_id)

    await tarea({}, request_id=12345)

    assert len(vistos) == 1
    assert validar_request_id(vistos[0]) == vistos[0]
