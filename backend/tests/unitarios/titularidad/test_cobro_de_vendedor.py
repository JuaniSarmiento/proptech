"""Lo que se le pide a un cobro de la cuenta del vendedor (4d, H-033): importe y fecha. Sin base."""

from datetime import date
from typing import Any

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.titularidad.dominio.cobro import CobroInvalido, validar_cobro

HOY = date(2026, 12, 15)


def _campo(importe: Any, fecha: Any, deuda: str = "1000.00") -> str:
    with pytest.raises(CobroInvalido) as error:
        validar_cobro(importe=importe, fecha=fecha, hoy=HOY, deuda=Dinero(deuda))
    return error.value.campo


def test_un_cobro_valido_devuelve_importe_y_fecha() -> None:
    assert validar_cobro(importe="250.5", fecha="2026-12-15", hoy=HOY, deuda=Dinero("1000.00")) == (
        Dinero("250.50"),
        HOY,
    )
    assert validar_cobro(importe="1000", fecha="2026-11-01", hoy=HOY, deuda=Dinero("1000.00"))[
        0
    ] == Dinero("1000.00")


@pytest.mark.parametrize(
    "importe",
    ["0", "0.00", "-1.00", "10.001", "1e2", "", " ", "abc", "\u0661\u0660", 100, 1.5, None, True],
)
def test_un_importe_que_no_sirve_se_rechaza(importe: Any) -> None:
    assert _campo(importe, "2026-12-10") == "importe"


def test_un_importe_mayor_que_la_deuda_o_sobre_una_cuenta_en_cero_se_rechaza() -> None:
    assert _campo("1000.01", "2026-12-10") == "importe"
    assert _campo("0.01", "2026-12-10", deuda="0.00") == "importe"


@pytest.mark.parametrize(
    "fecha",
    [
        "2026-12-16",
        "2026-13-01",
        "2026-12-32",
        "15/12/2026",
        "",
        None,
        20261210,
        "\u0662\u0660\u0662\u0666-\u0661\u0662-\u0661\u0660",
    ],
)
def test_una_fecha_futura_o_que_no_es_fecha_se_rechaza(fecha: Any) -> None:
    assert _campo("10.00", fecha) == "fecha"
