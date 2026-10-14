"""Tests unitarios de la política de reintentos (D3). Cambio 1c, tarea 5.3.

Escenarios de `cola-de-trabajos`: Falla pasajera y después éxito (esperas);
Intentos agotados (evento); Error que no es pasajero. Lecciones: L-007
(ninguno de los eventos repite el mensaje de la excepción).
"""

from typing import Any

import pytest
import redis.exceptions
import sqlalchemy.exc
from arq import Retry

from proptech_core.compartido.reintentos import ErrorPasajero, PoliticaReintentos, reintentable

pytestmark = pytest.mark.anyio

MARCADOR = "marcador-reintentos-7e2a1c"


def _politica(espera_base: float = 2.0, intentos_maximos: int = 5) -> PoliticaReintentos:
    return PoliticaReintentos(espera_base=espera_base, intentos_maximos=intentos_maximos)


def _ctx(intento: int, politica: PoliticaReintentos) -> dict[str, Any]:
    return {"job_try": intento, "politica": politica, "job_name": "tarea_de_prueba"}


@pytest.mark.parametrize(("intento", "espera_esperada"), [(1, 2.0), (2, 4.0), (3, 8.0), (4, 16.0)])
async def test_espera_se_duplica_en_cada_intento(intento: int, espera_esperada: float) -> None:
    @reintentable
    async def tarea(ctx: dict[str, Any]) -> None:
        raise ErrorPasajero(MARCADOR)

    with pytest.raises(Retry) as exc_info:
        await tarea(_ctx(intento, _politica()))
    assert exc_info.value.defer_score == espera_esperada * 1000


async def test_error_pasajero_loguea_reintento_programado(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")

    @reintentable
    async def tarea(ctx: dict[str, Any]) -> None:
        raise ErrorPasajero(MARCADOR)

    with pytest.raises(Retry):
        await tarea(_ctx(1, _politica()))

    registros = [r for r in caplog.records if r.msg == "reintento_programado"]
    assert len(registros) == 1
    registro = registros[0]
    assert registro.tarea == "tarea_de_prueba"  # type: ignore[attr-defined]
    assert registro.intento == 1  # type: ignore[attr-defined]
    assert registro.intentos_maximos == 5  # type: ignore[attr-defined]
    assert registro.espera_s == 2.0  # type: ignore[attr-defined]
    assert MARCADOR not in str(registro.__dict__)


async def test_intento_agotado_loguea_tarea_agotada_nivel_error_y_relanza(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")

    @reintentable
    async def tarea(ctx: dict[str, Any]) -> None:
        raise ErrorPasajero(MARCADOR)

    with pytest.raises(ErrorPasajero):
        await tarea(_ctx(5, _politica(intentos_maximos=5)))

    registros = [r for r in caplog.records if r.msg == "tarea_agotada"]
    assert len(registros) == 1
    registro = registros[0]
    assert registro.levelname == "ERROR"
    assert registro.intento == 5  # type: ignore[attr-defined]
    assert registro.intentos_maximos == 5  # type: ignore[attr-defined]
    assert MARCADOR not in str(registro.__dict__)
    assert not any(r.msg == "reintento_programado" for r in caplog.records)


async def test_error_no_pasajero_loguea_tarea_fallida_sin_reintento(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")

    @reintentable
    async def tarea(ctx: dict[str, Any]) -> None:
        raise ValueError(MARCADOR)

    with pytest.raises(ValueError):
        await tarea(_ctx(1, _politica()))

    registros = [r for r in caplog.records if r.msg == "tarea_fallida"]
    assert len(registros) == 1
    assert registros[0].levelname == "ERROR"
    assert MARCADOR not in str(registros[0].__dict__)
    assert not any(r.msg in ("reintento_programado", "tarea_agotada") for r in caplog.records)


@pytest.mark.parametrize(
    "error",
    [
        sqlalchemy.exc.OperationalError(MARCADOR, None, Exception(MARCADOR)),
        redis.exceptions.ConnectionError(MARCADOR),
        redis.exceptions.TimeoutError(MARCADOR),
        TimeoutError(MARCADOR),
        ConnectionError(MARCADOR),
        # Vuelta 3 (F2b, variante baja): pool de conexiones agotado, no sólo
        # la base caída o congelada.
        sqlalchemy.exc.TimeoutError(MARCADOR),
    ],
)
async def test_errores_pasajeros_por_naturaleza_se_reintentan(error: Exception) -> None:
    @reintentable
    async def tarea(ctx: dict[str, Any]) -> None:
        raise error

    with pytest.raises(Retry):
        await tarea(_ctx(1, _politica()))
