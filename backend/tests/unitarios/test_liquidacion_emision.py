"""Emitir lo revisado (H-013; E3, E7, E8), sin base: el pedido, las alertas aceptadas y la
composición de cada grupo."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from proptech_core.liquidacion.dominio.emision import (
    AlertasDistintas,
    ControlDuroActivo,
    PedidoInvalido,
    VencimientoCorrido,
    coeficientes_efectivos,
    pedido_de_emision,
    validar_alertas,
)

_PERIODO = date(2026, 11, 1)
_ID = "6f1f2b36-98a4-4f46-9d57-6a7a0a0b7f10"


def _cuerpo(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {"emision_id": _ID, "huella": "abc", "alertas_aceptadas": []}
    return {**base, **cambios}


def _control(codigo: str, nivel: str) -> dict[str, object]:
    return {"codigo": codigo, "nivel": nivel, "mensaje": "m", "detalle": {}}


# --- el pedido ------------------------------------------------------------------------------------


def test_un_pedido_minimo_es_valido() -> None:
    pedido = pedido_de_emision(_cuerpo(), _PERIODO)
    assert pedido.emision_id == UUID(_ID)
    assert (pedido.huella, pedido.alertas_aceptadas, pedido.vencimiento) == ("abc", (), None)


def test_el_vencimiento_nulo_es_el_de_la_configuracion() -> None:
    assert pedido_de_emision(_cuerpo(vencimiento=None), _PERIODO).vencimiento is None


def test_el_vencimiento_corrido_lleva_fecha_y_motivo_sin_espacios_de_mas() -> None:
    pedido = pedido_de_emision(
        _cuerpo(vencimiento={"fecha": "2026-11-12", "motivo": "  Feriado del 10/11 "}), _PERIODO
    )
    assert pedido.vencimiento == VencimientoCorrido(date(2026, 11, 12), "Feriado del 10/11")


@pytest.mark.parametrize(
    ("cuerpo", "campo"),
    [
        (_cuerpo(emision_id="no-es-uuid"), "emision_id"),
        (_cuerpo(huella=""), "huella"),
        (_cuerpo(huella=3), "huella"),
        ({"emision_id": _ID, "huella": "abc"}, "alertas_aceptadas"),
        (_cuerpo(alertas_aceptadas="gastos_en_revision"), "alertas_aceptadas"),
        (_cuerpo(alertas_aceptadas=[3]), "alertas_aceptadas"),
        (_cuerpo(vencimiento={"fecha": "2026-11-12"}), "vencimiento.motivo"),
        (_cuerpo(vencimiento={"fecha": "2026-11-12", "motivo": "   "}), "vencimiento.motivo"),
        (_cuerpo(vencimiento={"fecha": "2026-11-12", "motivo": "x" * 501}), "vencimiento.motivo"),
        (_cuerpo(vencimiento={"fecha": "2026-10-31", "motivo": "Antes"}), "vencimiento.fecha"),
        (_cuerpo(vencimiento={"fecha": "12/11/2026", "motivo": "Mal"}), "vencimiento.fecha"),
        (_cuerpo(vencimiento={"motivo": "Sin fecha"}), "vencimiento.fecha"),
        (_cuerpo(vencimiento="2026-11-12"), "vencimiento"),
        (_cuerpo(id="otro"), "id"),
    ],
)
def test_un_pedido_invalido_nombra_el_campo(cuerpo: dict[str, object], campo: str) -> None:
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_emision(cuerpo, _PERIODO)
    assert error.value.campo == campo


def test_el_motivo_de_exactamente_500_caracteres_es_valido() -> None:
    pedido = pedido_de_emision(
        _cuerpo(vencimiento={"fecha": "2026-11-01", "motivo": "x" * 500}), _PERIODO
    )
    assert pedido.vencimiento is not None and len(pedido.vencimiento.motivo) == 500


# --- las alertas ----------------------------------------------------------------------------------


def test_sin_controles_no_hay_nada_que_aceptar() -> None:
    assert validar_alertas([], ()) == ()


def test_las_advertencias_no_se_aceptan_ni_frenan() -> None:
    assert validar_alertas([_control("gastos_sin_ia", "advertencia")], ()) == ()


def test_el_conjunto_exacto_de_bloqueantes_se_acepta() -> None:
    controles = [
        _control("gastos_en_revision", "bloqueante"),
        _control("gastos_sin_ia", "advertencia"),
    ]
    assert validar_alertas(controles, ("gastos_en_revision",)) == ("gastos_en_revision",)


def test_un_duro_activo_frena_aunque_venga_aceptado() -> None:
    controles = [_control("bloque_negativo", "duro"), _control("gastos_en_revision", "bloqueante")]
    with pytest.raises(ControlDuroActivo) as error:
        validar_alertas(controles, ("bloque_negativo", "gastos_en_revision"))
    assert error.value.codigos == ("bloque_negativo",)


@pytest.mark.parametrize(
    "aceptadas",
    [
        (),
        ("gastos_en_revision", "gastos_sin_ia"),
        ("gastos_sin_ia",),
        ("otro",),
        ("gastos_en_revision", "gastos_en_revision"),
    ],
)
def test_aceptar_de_menos_de_mas_o_repetido_son_alertas_distintas(
    aceptadas: tuple[str, ...],
) -> None:
    controles = [
        _control("gastos_en_revision", "bloqueante"),
        _control("gastos_sin_ia", "advertencia"),
    ]
    with pytest.raises(AlertasDistintas):
        validar_alertas(controles, aceptadas)


def test_aceptar_algo_que_no_esta_activo_es_de_mas() -> None:
    with pytest.raises(AlertasDistintas):
        validar_alertas([], ("gastos_en_revision",))


# --- la composición -------------------------------------------------------------------------------


def test_el_coeficiente_efectivo_es_el_peso_sobre_la_suma_con_seis_decimales() -> None:
    a, b = uuid4(), uuid4()
    assert coeficientes_efectivos({a: Decimal("0.25"), b: Decimal("0.15")}) == {
        a: "0.625000",
        b: "0.375000",
    }


def test_en_partes_iguales_es_una_fraccion_redondeada_medio_hacia_arriba() -> None:
    ids = [uuid4() for _ in range(3)]
    efectivos = coeficientes_efectivos({i: Decimal(1) for i in ids})
    assert set(efectivos.values()) == {"0.333333"}
    dos = [uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4()]
    assert coeficientes_efectivos({i: Decimal(1) for i in dos[:6]})[dos[0]] == "0.166667"


def test_los_pesos_que_ya_suman_uno_quedan_igual() -> None:
    ids = [uuid4() for _ in range(4)]
    pesos = dict(zip(ids, map(Decimal, ("0.30", "0.30", "0.25", "0.15")), strict=True))
    assert list(coeficientes_efectivos(pesos).values()) == [
        "0.300000",
        "0.300000",
        "0.250000",
        "0.150000",
    ]
