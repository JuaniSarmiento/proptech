"""El QR de ARCA como dominio puro (R12, H-036): sin base ni imagen, sólo el texto del QR."""

from __future__ import annotations

import base64
import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from proptech_core.gastos.dominio.factura_qr import QrDescartado, interpretar_qr

CUIT = "30711111117"


def _cuit_valido(prefijo: int) -> str:
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    while True:
        digitos = [int(c) for c in str(prefijo)]
        v = 11 - sum(d * p for d, p in zip(digitos, pesos, strict=True)) % 11
        v = 0 if v == 11 else v
        if v != 10:
            return f"{prefijo}{v}"
        prefijo += 1


CUIT_OK = _cuit_valido(3071111111)


def _datos(**cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ver": 1,
        "fecha": "2026-10-14",
        "cuit": int(CUIT_OK),
        "ptoVta": 3,
        "tipoCmp": 11,
        "nroCmp": 1001,
        "importe": 1500.5,
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": 80,
        "nroDocRec": 20000000001,
        "tipoCodAut": "E",
        "codAut": 70417054367476,
    }
    base.update(cambios)
    return {k: v for k, v in base.items() if v is not None}


def _texto(datos: Any, host: str = "www.arca.gob.ar", crudo: str | None = None) -> str:
    cuerpo = crudo if crudo is not None else json.dumps(datos, separators=(",", ":"))
    return f"https://{host}/fe/qr/?p={base64.b64encode(cuerpo.encode()).decode()}"


def _motivo(texto: str) -> str:
    with pytest.raises(QrDescartado) as error:
        interpretar_qr(texto)
    return error.value.motivo


def test_un_qr_bueno_da_los_datos_con_el_importe_en_pesos() -> None:
    d = interpretar_qr(_texto(_datos()))
    assert (d.cuit, d.punto_de_venta, d.tipo_de_comprobante, d.numero_de_comprobante) == (
        CUIT_OK,
        "3",
        "11",
        "1001",
    )
    assert d.fecha == date(2026, 10, 14) and d.documento_receptor == "20000000001"
    assert d.importe.a_texto() == "1500.50"


def test_el_importe_es_importe_por_cotizacion_con_redondeo_medio_hacia_arriba() -> None:
    assert (
        interpretar_qr(_texto(_datos(moneda="DOL", ctz=65, importe=12100))).importe.a_texto()
        == "786500.00"
    )
    assert (
        interpretar_qr(_texto(_datos(moneda="DOL", ctz=1.5, importe=100.5))).importe.a_texto()
        == "150.75"
    )
    assert (
        interpretar_qr(_texto(_datos(moneda="DOL", ctz=1.005, importe=0.5))).importe.a_texto()
        == "0.50"
    )
    assert (
        interpretar_qr(_texto(_datos(moneda="DOL", ctz=1.01, importe=0.5))).importe.a_texto()
        == "0.51"
    )


def test_sin_receptor_el_documento_es_nulo() -> None:
    assert interpretar_qr(_texto(_datos(nroDocRec=None))).documento_receptor is None


@pytest.mark.parametrize(
    "host", ["www.arca.gob.ar", "arca.gob.ar", "www.afip.gob.ar", "afip.gob.ar", "WWW.ARCA.GOB.AR"]
)
def test_los_dos_dominios(host: str) -> None:
    assert interpretar_qr(_texto(_datos(), host)).cuit == CUIT_OK


@pytest.mark.parametrize(
    "texto",
    [
        "hola",
        "http://www.arca.gob.ar/fe/qr/?p=e30=",
        "https://www.arca.gob.ar.malo.invalid/fe/qr/?p=e30=",
        "https://malo-arca.gob.ar/fe/qr/?p=e30=",
        "https://www.arca.gob.ar@malo.invalid/fe/qr/?p=e30=",
        "https://www.arca.gob.ar:444/fe/qr/?p=e30=",
        "https://www.arca.gob.ar/otra/ruta/?p=e30=",
        "https://sub.arca.gob.ar/fe/qr/?p=e30=",
    ],
)
def test_dominio_ajeno(texto: str) -> None:
    assert _motivo(texto) == "dominio_ajeno"


@pytest.mark.parametrize(
    "datos", [_datos(ver=2), _datos(ver="1"), _datos(ver=None), _datos(ver=1.0), _datos(ver=True)]
)
def test_version_desconocida(datos: dict[str, Any]) -> None:
    assert _motivo(_texto(datos)) == "version_desconocida"


def test_json_invalido() -> None:
    assert _motivo(_texto(None, crudo="no json")) == "json_invalido"
    assert _motivo(_texto(None, crudo="[1]")) == "json_invalido"
    assert _motivo(_texto(None, crudo='{"ver": NaN}')) == "json_invalido"
    assert _motivo("https://www.arca.gob.ar/fe/qr/?p=%%%") == "json_invalido"
    assert _motivo("https://www.arca.gob.ar/fe/qr/") == "json_invalido"


@pytest.mark.parametrize(
    "cambio",
    [
        {"importe": "abc"},
        {"importe": True},
        {"importe": 0},
        {"importe": -1},
        {"importe": 10.123},
        {"importe": None},
        {"ctz": 0},
        {"ctz": "x"},
        {"ctz": None},
        {"importe": 1e30},
        {"importe": 0.01, "ctz": 0.1},
    ],
)
def test_importe_invalido(cambio: dict[str, Any]) -> None:
    assert _motivo(_texto(_datos(**cambio))) == "importe_invalido"


@pytest.mark.parametrize(
    "cambio",
    [
        {"cuit": int(CUIT_OK) + 1},
        {"cuit": "no"},
        {"cuit": True},
        {"nroCmp": None},
        {"ptoVta": "abc"},
        {"tipoCmp": 1.5},
        {"fecha": "2026-02-30"},
        {"fecha": "14/10/2026"},
        {"fecha": "20261014"},
        {"fecha": 20261014},
        {"nroDocRec": [1]},
    ],
)
def test_datos_invalidos(cambio: dict[str, Any]) -> None:
    assert _motivo(_texto(_datos(**cambio))) == "datos_invalidos"


def test_vale_el_primero_de_la_tabla() -> None:
    assert _motivo(_texto(_datos(ver=2, importe="x", cuit=1), "malo.invalid")) == "dominio_ajeno"
    assert _motivo(_texto(_datos(ver=2, importe="x", cuit=1))) == "version_desconocida"
    assert _motivo(_texto(_datos(importe="x", cuit=1))) == "importe_invalido"


def test_el_importe_decimal_no_pasa_por_float() -> None:
    d = interpretar_qr(
        _texto(
            None,
            crudo=(
                f'{{"ver":1,"fecha":"2026-10-14","cuit":{CUIT_OK},"ptoVta":1,"tipoCmp":1,'
                '"nroCmp":1,"importe":0.1,"moneda":"DOL","ctz":3,"tipoDocRec":80}'
            ),
        )
    )
    assert d.importe.decimal == Decimal("0.30")
