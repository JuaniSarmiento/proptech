"""El orden de los períodos para preliquidar (H-011; R40, D-157)."""

from datetime import date

from proptech_core.liquidacion.dominio.periodos import (
    PERIODO_ANTERIOR_SIN_EMITIR,
    PERIODO_EMITIDO,
    motivo_de_rechazo,
)

OCT, NOV, DIC, ENE = date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1)


def test_sin_emisiones_cualquier_periodo_es_el_primero() -> None:
    assert motivo_de_rechazo(DIC, []) is None


def test_el_siguiente_al_emitido_se_puede() -> None:
    assert motivo_de_rechazo(NOV, [OCT]) is None


def test_un_periodo_salteado_se_rechaza() -> None:
    assert motivo_de_rechazo(DIC, [OCT]) == PERIODO_ANTERIOR_SIN_EMITIR


def test_un_periodo_emitido_se_rechaza() -> None:
    assert motivo_de_rechazo(OCT, [OCT]) == PERIODO_EMITIDO
    assert motivo_de_rechazo(OCT, [date(2026, 9, 1), OCT]) == PERIODO_EMITIDO


def test_el_anterior_a_enero_es_diciembre_del_año_anterior() -> None:
    assert motivo_de_rechazo(ENE, [DIC]) is None
    assert motivo_de_rechazo(ENE, [NOV]) == PERIODO_ANTERIOR_SIN_EMITIR


def test_un_periodo_anterior_al_primero_emitido_no_se_puede() -> None:
    assert motivo_de_rechazo(date(2026, 9, 1), [OCT]) == PERIODO_ANTERIOR_SIN_EMITIR
