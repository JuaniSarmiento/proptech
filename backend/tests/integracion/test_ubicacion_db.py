"""2.4: migración `0023` — el `CHECK` "los tres o ninguno" de la ubicación
y que `localidad` quedó nullable. Subida/bajada se ejercitan además por
`test_rls_edificio.py::test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a`,
que atraviesa esta migración con un complejo "viejo" de verdad."""

import psycopg
import pytest

from ._edificios import Edificios

pytestmark = pytest.mark.integracion


def test_ubicacion_completa_se_guarda(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    fila = app_edificio.execute(
        "UPDATE complejo SET provincia_id='50', departamento_id='50007', "
        "localidad_id='50007010', calle_y_numero='Alsina 123' WHERE id=%s "
        "RETURNING provincia_id, departamento_id, localidad_id, calle_y_numero",
        (edificios.complejo_a,),
    ).fetchone()
    assert fila == ("50", "50007", "50007010", "Alsina 123")


def test_ubicacion_vacia_se_guarda(app_edificio: psycopg.Connection, edificios: Edificios) -> None:
    fila = app_edificio.execute(
        "SELECT provincia_id, departamento_id, localidad_id FROM complejo WHERE id=%s",
        (edificios.complejo_a,),
    ).fetchone()
    assert fila == (None, None, None)


@pytest.mark.parametrize(
    "asignacion",
    [
        "provincia_id='50'",
        "provincia_id='50', departamento_id='50007'",
        "departamento_id='50007', localidad_id='50007010'",
    ],
)
def test_ubicacion_a_medias_falla_por_check(
    app_edificio: psycopg.Connection, edificios: Edificios, asignacion: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        app_edificio.execute(
            f"UPDATE complejo SET {asignacion} WHERE id = %s",  # noqa: S608 (literales del test)
            (edificios.complejo_a,),
        )


def test_calle_y_numero_sin_limite_de_largo_en_la_base(
    app_edificio: psycopg.Connection, edificios: Edificios
) -> None:
    """H-8/D2: el máximo de 200 vive en la aplicación, no en un `CHECK` —
    igual que `localidad` hoy. Esto confirma que la base no lo impone (la
    API sí, tarea 2.6)."""
    calle_larga = "A" * 500
    fila = app_edificio.execute(
        "UPDATE complejo SET calle_y_numero=%s WHERE id=%s RETURNING calle_y_numero",
        (calle_larga, edificios.complejo_a),
    ).fetchone()
    assert fila == (calle_larga,)
