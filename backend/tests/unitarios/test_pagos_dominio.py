"""El dominio de `pagos` sin base (H-018, 8 · E2 a E4, D-163): normalización del banco y del número,
el tipo del comprobante por sus primeros bytes, el pedido de un pago y el estado derivado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from proptech_core.pagos.dominio.comprobante import (
    TAMANO_MAXIMO,
    ComprobanteInvalido,
    tipo_de_comprobante,
)
from proptech_core.pagos.dominio.estado import estado_del_pago
from proptech_core.pagos.dominio.normalizacion import normalizar
from proptech_core.pagos.dominio.pedido import PedidoInvalido, pedido_de_pago

HOY = date(2026, 11, 18)
UNIDAD = str(uuid4())
OTRA = str(uuid4())
COMPROBANTE = str(uuid4())


def _cuerpo(**cambios: Any) -> dict[str, Any]:
    cuerpo: dict[str, Any] = {
        "comprobante_id": COMPROBANTE,
        "banco": "Banco Nación",
        "numero_de_operacion": "12-345.678",
        "fecha_de_transferencia": "2026-11-05",
        "monto": "100.00",
        "cbu_origen": None,
        "partes": [{"unidad_id": UNIDAD, "importe": "100.00"}],
    }
    cuerpo.update(cambios)
    return cuerpo


# --- normalizar -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Banco Nación", "banconacion"),
        (" BANCO  NACIÓN ", "banconacion"),
        ("12-345.678", "12345678"),
        ("12 345 678", "12345678"),
        ("Ñandú", "nandu"),
        ("A\tB\nC", "abc"),
    ],
)
def test_normalizar_quita_espacios_guiones_puntos_mayusculas_y_tildes(
    texto: str, esperado: str
) -> None:
    assert normalizar(texto) == esperado


def test_normalizar_es_idempotente() -> None:
    assert normalizar(normalizar("  Mercado-Pago 9.9 ")) == normalizar("  Mercado-Pago 9.9 ")


# --- el tipo del comprobante ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("contenido", "tipo"),
    [
        (b"\xff\xd8\xff\xe0" + bytes(8), "jpeg"),
        (b"\x89PNG\r\n\x1a\n" + bytes(8), "png"),
        (b"%PDF-1.4\n" + bytes(8), "pdf"),
    ],
)
def test_el_tipo_sale_de_los_primeros_bytes(contenido: bytes, tipo: str) -> None:
    assert tipo_de_comprobante(contenido) == tipo


@pytest.mark.parametrize(
    "contenido",
    [b"", b"MZ\x90\x00" + bytes(8), b"texto plano", b"\xff\xd8", b"\x89PNG\r\n", b"%PDF"],
)
def test_otro_contenido_no_es_comprobante(contenido: bytes) -> None:
    with pytest.raises(ComprobanteInvalido):
        tipo_de_comprobante(contenido)


def test_el_limite_es_de_diez_megabytes_exactos() -> None:
    png = b"\x89PNG\r\n\x1a\n"
    assert tipo_de_comprobante(png + bytes(TAMANO_MAXIMO - len(png))) == "png"
    with pytest.raises(ComprobanteInvalido):
        tipo_de_comprobante(png + bytes(TAMANO_MAXIMO - len(png) + 1))


# --- el pedido de un pago -------------------------------------------------------------------------


def test_un_pedido_valido() -> None:
    pedido = pedido_de_pago(_cuerpo(), HOY)
    assert pedido.monto.a_texto() == "100.00"
    assert pedido.banco_normalizado == "banconacion"
    assert pedido.numero_normalizado == "12345678"
    assert pedido.fecha_de_transferencia == date(2026, 11, 5)
    assert [(p.unidad_id, p.importe.a_texto()) for p in pedido.partes] == [(UNIDAD, "100.00")]
    assert pedido.cbu_origen is None


def test_el_cbu_de_veintidos_digitos_entra() -> None:
    assert pedido_de_pago(_cuerpo(cbu_origen="0" * 22), HOY).cbu_origen == "0" * 22


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"monto": 100.5}, "monto"),
        ({"monto": "100"}, "monto"),
        ({"monto": "100.000"}, "monto"),
        ({"monto": "0.00", "partes": [{"unidad_id": UNIDAD, "importe": "0.00"}]}, "monto"),
        ({"monto": "-1.00"}, "monto"),
        ({"monto": "1" * 13 + ".00"}, "monto"),
        ({"monto": "\uff11\uff10\uff10.00"}, "monto"),
        ({"monto": "100.00\n"}, "monto"),
        ({"partes": []}, "partes"),
        ({"partes": "x"}, "partes"),
        ({"partes": [{"unidad_id": UNIDAD, "importe": "100.0"}]}, "partes"),
        ({"partes": [{"unidad_id": UNIDAD, "importe": "0.00"}]}, "partes"),
        ({"partes": [{"unidad_id": "no-es-uuid", "importe": "100.00"}]}, "partes"),
        ({"fecha_de_transferencia": "2026-11-19"}, "fecha_de_transferencia"),
        ({"fecha_de_transferencia": "2025-11-17"}, "fecha_de_transferencia"),
        ({"fecha_de_transferencia": "2026-02-30"}, "fecha_de_transferencia"),
        ({"fecha_de_transferencia": "2026-11-5"}, "fecha_de_transferencia"),
        ({"fecha_de_transferencia": 20261105}, "fecha_de_transferencia"),
        ({"banco": "   "}, "banco"),
        ({"banco": 7}, "banco"),
        ({"banco": "x" * 101}, "banco"),
        ({"banco": "---"}, "banco"),
        ({"banco": "a\x00b"}, "banco"),
        ({"numero_de_operacion": ""}, "numero_de_operacion"),
        ({"numero_de_operacion": "9" * 101}, "numero_de_operacion"),
        ({"numero_de_operacion": " - . "}, "numero_de_operacion"),
        ({"cbu_origen": "123"}, "cbu_origen"),
        ({"cbu_origen": "1" * 23}, "cbu_origen"),
        ({"cbu_origen": "a" * 22}, "cbu_origen"),
        ({"cbu_origen": 1234567890123456789012}, "cbu_origen"),
    ],
)
def test_un_pedido_invalido_nombra_su_campo(cambios: dict[str, Any], campo: str) -> None:
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(_cuerpo(**cambios), HOY)
    assert error.value.campo == campo


def test_los_bordes_de_la_fecha_entran() -> None:
    assert pedido_de_pago(_cuerpo(fecha_de_transferencia="2026-11-18"), HOY)
    assert pedido_de_pago(_cuerpo(fecha_de_transferencia="2025-11-18"), HOY)


def test_las_partes_que_no_suman_el_monto_son_partes() -> None:
    cuerpo = _cuerpo(monto="100.01")
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(cuerpo, HOY)
    assert error.value.campo == "partes"


def test_una_unidad_repetida_son_partes_aunque_sumen() -> None:
    partes = [{"unidad_id": UNIDAD, "importe": "50.00"}, {"unidad_id": UNIDAD, "importe": "50.00"}]
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(_cuerpo(partes=partes), HOY)
    assert error.value.campo == "partes"


def test_dos_unidades_que_suman_entran() -> None:
    partes = [
        {"unidad_id": UNIDAD, "importe": "43350.00"},
        {"unidad_id": OTRA, "importe": "37425.00"},
    ]
    pedido = pedido_de_pago(_cuerpo(monto="80775.00", partes=partes), HOY)
    assert sum((p.importe.decimal for p in pedido.partes), Decimal(0)) == Decimal("80775.00")


def test_el_primer_campo_que_falla_manda() -> None:
    """Orden del contrato: monto, partes, fecha, banco, número, cbu."""
    cuerpo = _cuerpo(monto="x", partes=[], fecha_de_transferencia="x", banco="", cbu_origen="1")
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(cuerpo, HOY)
    assert error.value.campo == "monto"
    cuerpo = _cuerpo(partes=[], fecha_de_transferencia="x", banco="", cbu_origen="1")
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(cuerpo, HOY)
    assert error.value.campo == "partes"
    cuerpo = _cuerpo(fecha_de_transferencia="x", banco="", cbu_origen="1")
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(cuerpo, HOY)
    assert error.value.campo == "fecha_de_transferencia"
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(_cuerpo(banco="", numero_de_operacion="", cbu_origen="1"), HOY)
    assert error.value.campo == "banco"
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(_cuerpo(numero_de_operacion="", cbu_origen="1"), HOY)
    assert error.value.campo == "numero_de_operacion"


def test_la_forma_va_antes_que_la_suma() -> None:
    """Un cbu inválido y partes que no suman: gana la forma del cbu (la suma se mira después)."""
    with pytest.raises(PedidoInvalido) as error:
        pedido_de_pago(_cuerpo(monto="100.01", cbu_origen="1"), HOY)
    assert error.value.campo == "cbu_origen"


def test_un_cuerpo_que_no_es_objeto_o_sin_campos_no_rompe() -> None:
    for cuerpo in ({}, {"monto": "1.00"}):
        with pytest.raises(PedidoInvalido):
            pedido_de_pago(cuerpo, HOY)


def test_el_comprobante_va_como_texto_sin_validar_aca() -> None:
    """Que exista y sea de la persona lo decide la base (después de la suma)."""
    assert pedido_de_pago(_cuerpo(comprobante_id="no-uuid"), HOY).comprobante_id == "no-uuid"


# --- el estado derivado ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("eventos", "estado"),
    [
        ([], "informado"),
        (["confirmado"], "confirmado"),
        (["rechazado"], "rechazado"),
        (["confirmado", "revertido"], "revertido"),
        (["confirmado", "reimputado"], "confirmado"),
        (["confirmado", "reimputado", "revertido"], "revertido"),
    ],
)
def test_el_estado_sale_del_ultimo_evento(eventos: list[str], estado: str) -> None:
    assert estado_del_pago(eventos) == estado
