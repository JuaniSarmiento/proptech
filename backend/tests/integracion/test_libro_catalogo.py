"""Claves compuestas del contrato D1, necesarias como destino de las FK."""

import pytest

from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion

CLAVES = [
    ("cuenta", "uq_cuenta_adm_id", ["administracion_id", "id"]),
    ("cuenta", "uq_cuenta_edificio_id", ["administracion_id", "complejo_id", "id"]),
    ("emision", "uq_emision_edificio_id", ["administracion_id", "complejo_id", "id"]),
    ("emision", "uq_emision_periodo_id", ["administracion_id", "complejo_id", "periodo", "id"]),
    (
        "obligacion",
        "uq_obligacion_cuenta_id",
        ["administracion_id", "complejo_id", "cuenta_id", "id"],
    ),
    ("movimiento", "uq_mov_adm_id", ["administracion_id", "id"]),
    (
        "movimiento",
        "uq_mov_sentido",
        ["administracion_id", "complejo_id", "cuenta_id", "id", "sentido"],
    ),
    (
        "movimiento",
        "uq_mov_correccion",
        ["administracion_id", "complejo_id", "cuenta_id", "id", "tipo", "importe"],
    ),
]


@pytest.mark.parametrize("tabla,nombre,columnas", CLAVES, ids=[n for _, n, _ in CLAVES])
def test_clave_referenciada(
    base_del_edificio: BaseDeEdificio, tabla: str, nombre: str, columnas: list[str]
) -> None:
    with arranque(base_del_edificio) as c:
        fila = c.execute(
            (
                "SELECT ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALI"
                "TY AS u(num,orden) JOIN pg_attribute a ON a.attrelid=k.conrelid A"
                "ND a.attnum=u.num ORDER BY u.orden) FROM pg_constraint k WHERE k."
                "conrelid=to_regclass(%s) AND k.conname=%s AND k.contype='u'"
            ),
            (tabla, nombre),
        ).fetchone()
        assert fila == (columnas,), f"falta la superclave {nombre}: {fila}"
