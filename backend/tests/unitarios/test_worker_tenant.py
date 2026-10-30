"""`con_administracion_de_tarea` (D4, D8, cambio 2a, tarea 7.1): validación y
reescritura de `clave`, sin tocar ninguna base real — sólo lo que el
decorador hace con sus argumentos.

Escenarios de `cola-de-trabajos`: Trabajo sin administración; Administración
malformada. Lecciones: L-007, L-008.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from proptech_core.compartido.tenant_de_tarea import (
    AdministracionInvalida,
    con_administracion_de_tarea,
)
from tests._registros_del_log import capturar_todo, fugas_del_valor

pytestmark = pytest.mark.anyio


@con_administracion_de_tarea
async def _tarea_de_eco(
    ctx: dict[str, Any], *, administracion_id: Any, clave: str | None = None, **datos: Any
) -> dict[str, Any]:
    return {"administracion_id": administracion_id, "clave": clave}


_VALORES_INVALIDOS = [
    pytest.param(None, id="faltante"),
    pytest.param("", id="vacio"),
    pytest.param("   ", id="en_blanco"),
    pytest.param(123, id="entero"),
    pytest.param("no-es-uuid", id="texto_no_uuid"),
    # Dígitos arábigos-índicos (U+0660 EXTENDED ARABIC-INDIC ZERO, etc.) con
    # la MISMA forma canónica que un UUID real: el patrón ASCII de D8 no los
    # confunde con dígitos hexadecimales, aunque `int()`/`str.isdigit()` sí
    # los reconozcan como "dígitos" para otros propósitos (L-008).
    pytest.param("12345678-1234-1234-1234-12345678901٦", id="digito_no_ascii"),
]


@pytest.mark.parametrize("valor", _VALORES_INVALIDOS)
async def test_administracion_invalida_falla_una_sola_vez_sin_efecto(
    valor: Any, caplog: pytest.LogCaptureFixture
) -> None:
    efecto_corrio = False

    @con_administracion_de_tarea
    async def _tarea_con_efecto(ctx: dict[str, Any], *, administracion_id: Any) -> None:
        nonlocal efecto_corrio
        efecto_corrio = True

    with capturar_todo(caplog):
        with pytest.raises(AdministracionInvalida):
            await _tarea_con_efecto({}, administracion_id=valor)

    assert efecto_corrio is False
    eventos = [r.getMessage() for r in caplog.records]
    assert "tarea_sin_administracion" in eventos
    # L-007: el valor rechazado nunca aparece en ningún registro del log.
    # `None`/`""` son triviales (cualquier string "contiene" ""; "None"
    # aparece siempre en el repr de un LogRecord por `exc_info`), así que
    # el chequeo real sólo tiene sentido para un valor con contenido propio.
    #
    # Deuda V3-8 (2a), tarea 4.1: comparar contra `str(registro.__dict__)`
    # entero es un flake, no una verificación (visto en 4 de 100 corridas,
    # siempre con `valor=123`): ese diccionario trae metadata propia de
    # `LogRecord` que nada tiene que ver con el valor rechazado —
    # `created` (segundos con fracción), `thread`, `process`, `taskName`
    # de asyncio— y cualquiera de ellos puede CONTENER por azar los mismos
    # dígitos ("123" en el id de un hilo o en los microsegundos de
    # `created`).
    #
    # C2-6 (rompedor/auditor, vuelta 1 del 2c): comparar sólo contra el
    # campo `tarea` (como quedó después del arreglo del flake de arriba)
    # le sacó los dientes al test para cualquier OTRA fuga: una fuga en un
    # campo extra nuevo (`valor_recibido`, o el `causa` que agregó la
    # tarea 6.1) pasaba sin que nada la viera (M10 y M10b del rompedor,
    # L-019/L-020). Se compara contra TODOS los campos extra del
    # registro — `__dict__` menos los atributos estándar de un
    # `LogRecord` recién creado (`_ATRIBUTOS_ESTANDAR` de `logs.py`, el
    # mismo criterio que usa `FormateadorJSON` para separar "extra" de lo
    # propio del logger) — sin importar cómo se llame el campo nuevo que
    # alguien agregue el día de mañana.
    #
    # C2V2-2 y N-b (2e): se captura TODO (cualquier nivel y logger: un `WARNING` con el valor en
    # otro módulo también cuenta) y se busca el valor por igualdad / palabra aparte, no con
    # `representacion in str(campos)`, que daba rojo falso con "123" dentro de `1230` o `a1234`.
    # Ver `tests/_registros_del_log.py` y `test_registros_del_log.py`.
    if str(valor) not in ("", "None"):
        assert fugas_del_valor(caplog.records, valor) == []


async def test_administracion_valida_le_llega_a_la_tarea_como_uuid() -> None:
    administracion_id = uuid.uuid4()
    resultado = await _tarea_de_eco({}, administracion_id=str(administracion_id))
    assert resultado["administracion_id"] == administracion_id
    assert isinstance(resultado["administracion_id"], uuid.UUID)


async def test_la_clave_de_idempotencia_lleva_el_administracion_id_adentro() -> None:
    administracion_id = uuid.uuid4()
    resultado = await _tarea_de_eco(
        {}, administracion_id=str(administracion_id), clave="algo-logico"
    )
    assert resultado["clave"] == f"{administracion_id}:algo-logico"


async def test_sin_clave_no_agrega_nada() -> None:
    administracion_id = uuid.uuid4()
    resultado = await _tarea_de_eco({}, administracion_id=str(administracion_id))
    assert resultado["clave"] is None


async def test_reintentable_nunca_corre_si_la_administracion_es_invalida() -> None:
    """D3: este decorador va POR FUERA de `reintentable` en la pila, así que
    un `administracion_id` inválido ni siquiera llega a invocar la función
    envuelta por `reintentable` — nunca hay "reintento 1 de 5", hay cero."""
    from proptech_core.compartido.reintentos import reintentable

    llamadas = 0

    @con_administracion_de_tarea
    @reintentable
    async def _tarea(ctx: dict[str, Any], *, administracion_id: Any) -> None:
        nonlocal llamadas
        llamadas += 1

    with pytest.raises(AdministracionInvalida):
        await _tarea({"job_try": 1, "politica": None}, administracion_id="no-es-uuid")
    assert llamadas == 0
