"""QA-9: privilegio exacto del UPDATE y cero incluido en el CHECK, como app real."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest

from ._edificios import BaseDeEdificio
from ._libro import sembrar_libro
from .test_umbral_migracion import insertar

pytestmark = pytest.mark.integracion


def test_qa9_sqlstate_de_update_del_umbral(base_del_edificio: BaseDeEdificio) -> None:
    estado = None
    with base_del_edificio.conectar_app() as c:
        try:
            c.execute("UPDATE configuracion_versionada SET umbral_saldo_chico=0 WHERE false")
        except psycopg.Error as error:
            estado = error.sqlstate
    assert estado == "42501"


@pytest.mark.parametrize("umbral", ["0.00", "0.01"])
def test_qa9_borde_inclusivo_del_check(base_del_edificio: BaseDeEdificio, umbral: str) -> None:
    estado = None
    with base_del_edificio.conectar_app() as c, c.transaction():
        datos = sembrar_libro(c)
        try:
            with c.transaction():
                insertar(
                    c,
                    datos.admin,
                    datos.edificios.complejo_a,
                    datos.persona,
                    date(2026, 11, 1),
                    umbral,
                )
        except psycopg.Error as error:
            estado = error.sqlstate
        filas = c.execute(
            "SELECT umbral_saldo_chico FROM configuracion_versionada WHERE complejo_id=%s",
            (datos.edificios.complejo_a,),
        ).fetchall()
    assert (estado, filas) == (None, [(Decimal(umbral),)])
