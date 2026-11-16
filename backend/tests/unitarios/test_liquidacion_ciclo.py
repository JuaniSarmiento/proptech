"""El ciclo de una liquidación emitida (E9, E10, P26, P39, D-157), sin base."""

from uuid import UUID

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.liquidacion.dominio.ciclo import (
    PedidoInvalido,
    conflicto_al_anular,
    conflicto_al_distribuir,
    pedido_de_anulacion,
    pedido_de_cargo,
    visible_para_el_consejo,
)


def test_una_emitida_se_anula() -> None:
    assert conflicto_al_anular("emitida", siguiente_emitido=False) is None


def test_una_distribuida_no_se_anula() -> None:
    assert conflicto_al_anular("distribuida", siguiente_emitido=False) == (
        "estado",
        "ya_distribuida",
    )


def test_una_anulada_no_se_anula_otra_vez() -> None:
    assert conflicto_al_anular("anulada", siguiente_emitido=False) == ("estado", "anulada")


def test_con_el_periodo_siguiente_emitido_no_se_anula() -> None:
    assert conflicto_al_anular("emitida", siguiente_emitido=True) == (
        "periodo",
        "periodo_siguiente_emitido",
    )


def test_el_estado_manda_sobre_el_periodo_siguiente() -> None:
    assert conflicto_al_anular("distribuida", siguiente_emitido=True) == (
        "estado",
        "ya_distribuida",
    )


def test_una_emitida_se_distribuye() -> None:
    assert conflicto_al_distribuir("emitida") is None


@pytest.mark.parametrize(
    ("estado", "motivo"), [("distribuida", "ya_distribuida"), ("anulada", "anulada")]
)
def test_no_se_distribuye_lo_distribuido_ni_lo_anulado(estado: str, motivo: str) -> None:
    assert conflicto_al_distribuir(estado) == ("estado", motivo)


@pytest.mark.parametrize(
    ("estado", "visible"), [("emitida", False), ("distribuida", True), ("anulada", False)]
)
def test_el_consejo_sólo_ve_lo_distribuido(estado: str, visible: bool) -> None:
    assert visible_para_el_consejo(estado) is visible


# --- el cuerpo de anular y el del cargo cobrado de menos -----------------------------------------

_ID = "6f1f2b36-98a4-4f46-9d57-6a7a0a0b7f10"
_OTRO = "0b5b6c2a-1d55-4bd4-9d0e-5f5d3c1f1a01"


def test_el_motivo_de_anular_se_recorta() -> None:
    assert (
        pedido_de_anulacion({"motivo": "  Se cargó mal una factura  "})
        == "Se cargó mal una factura"
    )


@pytest.mark.parametrize(
    "cuerpo", [{}, {"motivo": ""}, {"motivo": "   "}, {"motivo": 5}, {"motivo": "x" * 501}]
)
def test_anular_sin_motivo_valido_es_invalido(cuerpo: dict[str, object]) -> None:
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_anulacion(cuerpo)
    assert error.value.campo == "motivo"


def test_anular_no_admite_otros_campos() -> None:
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_anulacion({"motivo": "ok", "estado": "anulada"})
    assert error.value.campo == "estado"


def _cargo(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "operacion_id": _ID,
        "obligacion_origen_id": _OTRO,
        "importe": "1500.00",
        "componente": "ordinaria",
        "motivo": "Faltó cobrar el portón",
    }
    return {**base, **cambios}


def test_un_cargo_valido() -> None:
    pedido = pedido_de_cargo(_cargo())
    assert pedido.operacion_id == UUID(_ID) and pedido.obligacion_origen_id == UUID(_OTRO)
    assert pedido.importe == Dinero("1500.00")
    assert (pedido.componente, pedido.motivo) == ("ordinaria", "Faltó cobrar el portón")


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"operacion_id": "no-es-uuid"}, "operacion_id"),
        ({"obligacion_origen_id": 5}, "obligacion_origen_id"),
        ({"importe": 1500}, "importe"),
        ({"importe": "mucho"}, "importe"),
        ({"componente": "interes"}, "componente"),
        ({"motivo": "  "}, "motivo"),
        ({"id": _ID}, "id"),
        ({"administracion_id": _ID}, "administracion_id"),
    ],
)
def test_un_cargo_invalido_nombra_el_campo(cambios: dict[str, object], campo: str) -> None:
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_cargo(_cargo(**cambios))
    assert error.value.campo == campo


def test_un_cargo_sin_un_campo_obligatorio_es_invalido() -> None:
    cuerpo = _cargo()
    del cuerpo["importe"]
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_cargo(cuerpo)
    assert error.value.campo == "importe"
