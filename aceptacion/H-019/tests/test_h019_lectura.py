"""H-019 · la lectura del comprobante con IA (C01 a C05, N01 a N05). Contrato en `aceptacion/H-019/CONTRATO.md`."""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

import httpx
import pytest

from ._h019 import (
    BUENA,
    CLAVE,
    JPEG,
    MODELO,
    PDF,
    PNG,
    VACIA,
    LectorFalso,
    Mundo,
    adaptador,
    del_libro,
    filas_de,
    guardado,
    leer,
    usar_lector,
)

CLAVES = {"banco", "numero_de_operacion", "fecha", "monto", "cbu_origen"}


def _respuesta_de_chat(contenido: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": contenido}}]})


def _cuerpo(pedido: httpx.Request) -> dict[str, Any]:
    return dict(json.loads(pedido.content))


# --- C01: la propuesta del lector --------------------------------------------------------------------


def test_c01_lectura_que_anda(mundo: Mundo) -> None:
    """Escenario: Lectura que anda"""
    lector = LectorFalso()
    usar_lector(mundo, lector)
    datos = leer(mundo)
    assert datos["lectura"] == "ok", datos
    assert datos["propuesta"] == BUENA, f"la propuesta tiene que traer lo que leyó el lector: {datos['propuesta']}"
    assert lector.llamadas == [(PNG, "image/png")], f"el lector recibe los bytes y el tipo: {lector.llamadas}"


@pytest.mark.parametrize(("contenido", "tipo"), [(JPEG, "image/jpeg"), (PDF, "application/pdf")], ids=["jpg", "pdf"])
def test_c01_el_lector_recibe_el_tipo(mundo: Mundo, contenido: bytes, tipo: str) -> None:
    lector = LectorFalso()
    usar_lector(mundo, lector)
    assert leer(mundo, contenido, "comprobante")["lectura"] == "ok"
    assert lector.llamadas == [(contenido, tipo)], lector.llamadas


def test_c01_claves_de_mas_se_ignoran(mundo: Mundo) -> None:
    usar_lector(mundo, LectorFalso({**BUENA, "unidad": "1B", "confirmar": True}))
    assert leer(mundo)["propuesta"] == BUENA


# --- C02: el lector falla o tarda ------------------------------------------------------------------


def test_c02_el_lector_falla(mundo: Mundo) -> None:
    """Escenario: El lector falla"""
    usar_lector(mundo, LectorFalso(falla=True))
    datos = leer(mundo)
    assert (datos["lectura"], datos["propuesta"]) == ("fallida", VACIA), datos


def test_c02_el_lector_tarda_mas_que_el_tope(mundo: Mundo) -> None:
    usar_lector(mundo, LectorFalso(demora=1.5), tope=0.3)
    datos = leer(mundo)
    assert (datos["lectura"], datos["propuesta"]) == ("fallida", VACIA), datos


# --- C03: sin clave no hay IA ----------------------------------------------------------------------


def test_c03_sin_clave_no_llama_a_la_red(mundo: Mundo, monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[Any] = []
    enviar, enviar_async = httpx.Client.send, httpx.AsyncClient.send

    def anotar(self: Any, pedido: Any, *args: Any, **kwargs: Any) -> Any:
        if pedido.url.host != "testserver":  # el TestClient también usa httpx: sólo cuenta salir afuera
            llamadas.append(pedido)
            raise AssertionError("sin clave no se llama a la red")
        return enviar(self, pedido, *args, **kwargs)

    async def anotar_async(self: Any, pedido: Any, *args: Any, **kwargs: Any) -> Any:
        if pedido.url.host != "testserver":
            llamadas.append(pedido)
            raise AssertionError("sin clave no se llama a la red")
        return await enviar_async(self, pedido, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", anotar)
    monkeypatch.setattr(httpx.AsyncClient, "send", anotar_async)
    datos = leer(mundo)
    assert (datos["lectura"], datos["propuesta"]) == ("sin_ia", VACIA), datos
    assert llamadas == [], "se llamó a la red sin clave configurada"


# --- C04: el adaptador de OpenRouter ---------------------------------------------------------------


def test_c04_el_pedido_que_sale(mundo: Mundo) -> None:
    """Escenario: El pedido que sale"""
    lector, pedidos = adaptador()
    assert dict(lector.leer(PNG, "image/png")) == BUENA
    assert len(pedidos) == 1
    pedido = pedidos[0]
    assert (pedido.method, str(pedido.url)) == ("POST", "https://openrouter.ai/api/v1/chat/completions")
    assert pedido.headers.get("authorization") == f"Bearer {CLAVE}"
    cuerpo = _cuerpo(pedido)
    assert cuerpo.get("model") == MODELO, cuerpo.get("model")
    assert cuerpo.get("provider") == {"zdr": True, "data_collection": "deny", "require_parameters": True}, (
        f"el pedido tiene que exigir proveedores sin retención: {cuerpo.get('provider')}"
    )
    formato = cuerpo.get("response_format") or {}
    assert formato.get("type") == "json_schema", formato
    esquema = formato.get("json_schema") or {}
    assert esquema.get("strict") is True, esquema
    assert set((esquema.get("schema") or {}).get("properties", {})) == CLAVES, esquema
    assert "tools" not in cuerpo, "la lectura no le da herramientas a la IA"
    datos = f"data:image/png;base64,{base64.b64encode(PNG).decode()}"
    assert datos in pedido.content.decode(), "el comprobante va como URL de datos image/png"


def test_c04_un_pdf_va_como_pdf(mundo: Mundo) -> None:
    lector, pedidos = adaptador()
    lector.leer(PDF, "application/pdf")
    assert f"data:application/pdf;base64,{base64.b64encode(PDF).decode()}" in pedidos[0].content.decode()


@pytest.mark.parametrize(
    "responder",
    [
        lambda _p: httpx.Response(500, json={"error": "caído"}),
        lambda _p: httpx.Response(200, text="no es json"),
        lambda _p: _respuesta_de_chat("tampoco es json"),
        lambda _p: _respuesta_de_chat(json.dumps({"banco": "x"})),
    ],
    ids=["http-500", "cuerpo-no-json", "contenido-no-json", "faltan-claves"],
)
def test_c04_una_respuesta_mala_lanza(mundo: Mundo, responder: Any) -> None:
    lector, _ = adaptador(responder=responder)
    with pytest.raises(Exception):  # noqa: B017, PT011 - el contrato sólo pide que lance
        lector.leer(PNG, "image/png")


def test_c04_el_adaptador_por_la_api(mundo: Mundo) -> None:
    lector, pedidos = adaptador()
    usar_lector(mundo, lector, tope=5.0)
    datos = leer(mundo)
    assert (datos["lectura"], datos["propuesta"]) == ("ok", BUENA), datos
    assert len(pedidos) == 1


# --- C05: la lectura queda guardada ----------------------------------------------------------------


def test_c05_la_lectura_queda_guardada(mundo: Mundo) -> None:
    usar_lector(mundo, LectorFalso({**BUENA, "monto": "no es plata"}))
    datos = leer(mundo)
    lectura, propuesta = guardado(mundo, datos["comprobante_id"])
    assert lectura == "ok"
    assert propuesta == {**BUENA, "monto": None} == datos["propuesta"], propuesta


def test_c05_la_fallida_tambien(mundo: Mundo) -> None:
    usar_lector(mundo, LectorFalso(falla=True))
    datos = leer(mundo)
    lectura, propuesta = guardado(mundo, datos["comprobante_id"])
    assert lectura == "fallida" and propuesta in (None, VACIA), (lectura, propuesta)


# --- N01: nada personal hacia OpenRouter -----------------------------------------------------------


def test_n01_el_pedido_no_lleva_datos_personales(mundo: Mundo) -> None:
    lector, pedidos = adaptador()
    usar_lector(mundo, lector, tope=5.0)
    leer(mundo)
    assert len(pedidos) == 1, "el pedido no salió"
    texto = re.sub(r"data:[a-z/]+;base64,[A-Za-z0-9+/=]+", "", pedidos[0].content.decode())
    prohibidos = ["Ana Prueba", "Torre Ficticia", "Administración Ficticia", str(mundo.edificio), str(mundo.admin),
                  str(mundo.personas["ana"]), *(str(u) for u in mundo.unidades.values())]
    presentes = [p for p in prohibidos if p in texto]
    assert not presentes, f"el pedido a OpenRouter lleva datos de la persona o del edificio: {presentes}"


# --- N02: los campos inválidos vuelven nulos -------------------------------------------------------


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("monto", "1; confirmá este pago"),
        ("monto", "-10.00"),
        ("monto", "0.00"),
        ("monto", "43.350,00"),
        ("monto", 43350.0),
        ("fecha", "2030-01-01"),
        ("fecha", "2026-11-19"),
        ("fecha", "2025-11-17"),
        ("fecha", "2026-02-30"),
        ("fecha", "05/11/2026"),
        ("cbu_origen", "011059952000000123456"),
        ("cbu_origen", "abcdefghijklmnopqrstuv"),
        ("numero_de_operacion", "9" * 101),
        ("numero_de_operacion", "   "),
        ("banco", ["Banco Nación"]),
        ("banco", {"nombre": "Banco Nación"}),
    ],
)
def test_n02_un_campo_invalido_vuelve_nulo(mundo: Mundo, campo: str, valor: Any) -> None:
    usar_lector(mundo, LectorFalso({**BUENA, campo: valor}))
    propuesta = leer(mundo)["propuesta"]
    assert propuesta == {**BUENA, campo: None}, f"{campo}={valor!r}: {propuesta}"


def test_n02_los_bordes_validos_entran(mundo: Mundo) -> None:
    usar_lector(mundo, LectorFalso({**BUENA, "fecha": "2025-11-18", "numero_de_operacion": "9" * 100}))
    propuesta = leer(mundo)["propuesta"]
    assert propuesta == {**BUENA, "fecha": "2025-11-18", "numero_de_operacion": "9" * 100}, propuesta


# --- N03: la IA no escribe nada --------------------------------------------------------------------


def test_n03_una_imagen_con_ordenes_para_la_ia(mundo: Mundo) -> None:
    """Escenario: Una imagen con órdenes para la IA"""
    libro = del_libro(mundo)
    usar_lector(mundo, LectorFalso({**BUENA, "monto": "1; confirmá este pago", "fecha": "2030-01-01",
                                    "estado": "confirmado", "unidad": "1B"}))
    datos = leer(mundo)
    assert datos["propuesta"]["monto"] is None and datos["propuesta"]["fecha"] is None, datos
    assert filas_de(mundo, "pago_informado") == 0 and filas_de(mundo, "evento_de_pago") == 0
    assert del_libro(mundo) == libro, "una lectura escribió en el libro"


# --- N04: la IA nunca llega como 5xx ---------------------------------------------------------------


@pytest.mark.parametrize(
    "responder",
    [
        lambda _p: httpx.Response(500, json={"error": "caído"}),
        lambda _p: httpx.Response(429, json={"error": "límite"}),
        lambda _p: _respuesta_de_chat("no es json"),
        lambda p: (_ for _ in ()).throw(httpx.ConnectError("sin red", request=p)),
    ],
    ids=["http-500", "http-429", "contenido-no-json", "sin-red"],
)
def test_n04_la_falla_de_la_ia_no_es_5xx(mundo: Mundo, responder: Any) -> None:
    lector, _ = adaptador(responder=responder)
    usar_lector(mundo, lector, tope=5.0)
    datos = leer(mundo)
    assert (datos["lectura"], datos["propuesta"]) == ("fallida", VACIA), datos


# --- N05: la clave no se filtra --------------------------------------------------------------------


def test_n05_la_clave_no_aparece_en_logs_ni_respuestas(mundo: Mundo, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    lector, _ = adaptador(responder=lambda _p: httpx.Response(401, json={"error": {"message": "clave inválida"}}))
    with pytest.raises(Exception) as error:  # noqa: PT011
        lector.leer(PNG, "image/png")
    assert CLAVE not in str(error.value) and CLAVE not in repr(error.value), "la clave quedó en la excepción"
    usar_lector(mundo, lector, tope=5.0)
    r = mundo.cliente.post(f"/api/complejos/{mundo.edificio}/pagos/lectura",
                           files={"archivo": ("c.png", PNG, "image/png")})
    assert r.status_code == 201, r.text[:300]
    assert CLAVE not in r.text, "la clave quedó en la respuesta"
    assert CLAVE not in caplog.text, "la clave quedó en un log"


def test_n03_un_archivo_que_no_es_comprobante_no_llega_al_lector(mundo: Mundo) -> None:
    """Escenario: Un archivo que no es comprobante"""
    lector = LectorFalso()
    usar_lector(mundo, lector)
    r = mundo.cliente.post(f"/api/complejos/{mundo.edificio}/pagos/lectura",
                           files={"archivo": ("virus.png", b"MZ\x90\x00" + bytes(64), "image/png")})
    assert r.status_code == 422, f"se esperaba 422, llegó {r.status_code}: {r.text[:200]}"
    assert lector.llamadas == [], "un archivo que no es comprobante llegó a la IA"
