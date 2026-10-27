"""3.2/3.4: `complejo.pisos`/`subsuelos` (migración `0024`) — nullable,
rango 1-60 / 0-5, sin backfill (D3, corrección DBA-1)."""

import psycopg
import pytest

from ._edificios import Edificios

pytestmark = pytest.mark.integracion


def test_pisos_y_subsuelos_nacen_nulos_sin_backfill(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """Un edificio que ya existía antes de `0024` (como los que siembra
    `edificios`) queda con `pisos`/`subsuelos` en `NULL` — nunca calculado
    de las unidades existentes."""
    fila = app_edificio.execute(
        "SELECT pisos, subsuelos FROM complejo WHERE id = %s", (edificios.complejo_a,)
    ).fetchone()
    assert fila == (None, None)


def test_pisos_dentro_de_rango_se_guarda(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    fila = app_edificio.execute(
        "UPDATE complejo SET pisos = 60, subsuelos = 5 WHERE id = %s RETURNING pisos, subsuelos",
        (edificios.complejo_a,),
    ).fetchone()
    assert fila == (60, 5)


@pytest.mark.parametrize("asignacion", ["pisos = 0", "pisos = 61", "pisos = -1"])
def test_pisos_fuera_de_rango_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, asignacion: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            f"UPDATE complejo SET {asignacion} WHERE id = %s",  # noqa: S608 (literales del test)
            (edificios.complejo_a,),
        )


@pytest.mark.parametrize("asignacion", ["subsuelos = -1", "subsuelos = 6"])
def test_subsuelos_fuera_de_rango_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, asignacion: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            f"UPDATE complejo SET {asignacion} WHERE id = %s",  # noqa: S608 (literales del test)
            (edificios.complejo_a,),
        )


def test_subsuelos_cero_es_valido(app_edificio: psycopg.Connection, edificios: Edificios) -> None:
    fila = app_edificio.execute(
        "UPDATE complejo SET subsuelos = 0 WHERE id = %s RETURNING subsuelos",
        (edificios.complejo_a,),
    ).fetchone()
    assert fila == (0,)
