"""H-037 (D-164, D-169): el adaptador de OpenRouter para facturas, sin llamar al servicio real.

Un transporte falso de httpx recibe el pedido y devuelve lo que cada caso necesita.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from proptech_core.gastos.adaptadores.openrouter import LectorDeFacturaOpenRouter, LecturaFallida

CLAVE = "sk-or-clave-secreta-de-prueba"
CATEGORIAS = [{"id": "11111111-1111-1111-1111-111111111111", "nombre": "Ascensores"}]
GRUPOS = [{"id": "22222222-2222-2222-2222-222222222222", "nombre": "Generales"}]
PROPUESTA = {
    "concepto": "Ascensores",
    "periodo": "2026-10",
    "categoria_id": None,
    "grupo_id": None,
    "importe": "1500.50",
}


def lector(respuesta: httpx.Response, pedidos: list[httpx.Request] | None = None) -> Any:
    def atender(pedido: httpx.Request) -> httpx.Response:
        if pedidos is not None:
            pedidos.append(pedido)
        return respuesta

    cliente = httpx.Client(transport=httpx.MockTransport(atender))
    return LectorDeFacturaOpenRouter(CLAVE, "proveedor/modelo", cliente)


def buena(**uso: Any) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "proveedor/modelo-resuelto",
            "choices": [{"message": {"content": json.dumps(PROPUESTA)}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 80, "cost": 0.001234} | uso,
        },
    )


def test_devuelve_la_propuesta_y_el_uso_de_la_respuesta() -> None:
    lectura = lector(buena()).leer(
        b"%PDF-1", "application/pdf", categorias=CATEGORIAS, grupos=GRUPOS
    )
    assert lectura.propuesta == PROPUESTA
    assert lectura.modelo == "proveedor/modelo-resuelto"
    assert (lectura.tokens_entrada, lectura.tokens_salida) == (1200, 80)
    assert lectura.costo == "0.001234"


def test_el_pedido_exige_zdr_salida_estricta_y_no_da_herramientas() -> None:
    pedidos: list[httpx.Request] = []
    lector(buena(), pedidos).leer(b"\x89PNG", "image/png", categorias=CATEGORIAS, grupos=GRUPOS)
    [pedido] = pedidos
    cuerpo = json.loads(pedido.content)
    assert cuerpo["provider"] == {
        "zdr": True,
        "data_collection": "deny",
        "require_parameters": True,
    }
    assert cuerpo["response_format"]["json_schema"]["strict"] is True
    assert cuerpo["usage"] == {"include": True}
    assert "tools" not in cuerpo and "tool_choice" not in cuerpo
    assert pedido.headers["authorization"] == f"Bearer {CLAVE}"
    texto = cuerpo["messages"][0]["content"][0]["text"]
    assert CATEGORIAS[0]["id"] in texto and "Ascensores" in texto and GRUPOS[0]["id"] in texto


def test_un_error_del_proveedor_no_lleva_la_clave_ni_el_pedido() -> None:
    with pytest.raises(LecturaFallida) as error:
        lector(httpx.Response(503, text=CLAVE)).leer(
            b"%PDF-1", "application/pdf", categorias=CATEGORIAS, grupos=GRUPOS
        )
    assert CLAVE not in str(error.value) and "503" in str(error.value)


def test_una_respuesta_ilegible_falla_pero_trae_lo_que_cobro() -> None:
    ilegible = httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "no es json"}}],
            "usage": {"prompt_tokens": 700, "completion_tokens": 5, "cost": 0.0005},
        },
    )
    with pytest.raises(LecturaFallida) as error:
        lector(ilegible).leer(b"%PDF-1", "application/pdf", categorias=[], grupos=[])
    assert (error.value.tokens_entrada, error.value.tokens_salida) == (700, 5)
    assert error.value.costo == "0.0005"
