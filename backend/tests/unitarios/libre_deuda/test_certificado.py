"""El contenido, la huella y el HTML del certificado de libre deuda (H-041, R21). Sin base."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from proptech_core.compartido.enlaces import EnlaceAlterado, EnlaceVencido, firmar
from proptech_core.libre_deuda.aplicacion.enlaces import firmar_enlace, verificar_enlace
from proptech_core.libre_deuda.dominio.certificado import (
    contenido_del_certificado,
    html_del_certificado,
    huella_del_certificado,
    monto_para_el_pdf,
)

CLAVE = "clave-de-prueba-de-enlaces-firmados-0123456789"
CORTE = date(2026, 11, 5)
CUOTA = {"periodo": "2026-11-01", "vencimiento": "2026-11-10", "importe": "10000.00"}
PAGO = {
    "pago_id": "00000000-0000-4000-8000-000000000001",
    "importe": "3000.00",
    "fecha_de_transferencia": "2026-11-02",
    "banco": "Banco <Nación>",
    "numero_de_operacion": "OP-0002",
}


def _contenido(**cambios: object) -> dict[str, Any]:
    base: dict[str, object] = {
        "unidad_id": "u1",
        "fecha_de_corte": CORTE,
        "capital": "20000.00",
        "intereses": "720.00",
        "interes_corrido": "100.00",
        "en_revision": [PAGO],
        "vencen_despues": [CUOTA],
    }
    return contenido_del_certificado(**{**base, **cambios})  # type: ignore[arg-type]


def _html(contenido: dict[str, Any]) -> str:
    return html_del_certificado(
        contenido,
        certificado_id=str(uuid4()),
        nombre_del_edificio="Torre Ficticia",
        identificador_de_la_unidad="1A",
    )


def test_el_saldo_es_el_capital_mas_los_intereses_y_no_incluye_el_corrido() -> None:
    contenido = _contenido()
    assert contenido["saldo"] == "20720.00"
    assert contenido["interes_corrido"] == "100.00"


def test_la_huella_es_hexadecimal_de_64_y_determinista() -> None:
    uno, dos = huella_del_certificado(_contenido()), huella_del_certificado(_contenido())
    assert uno == dos and len(uno) == 64 and uno == uno.lower()
    int(uno, 16)


@pytest.mark.parametrize(
    "cambio",
    [
        {"unidad_id": "u2"},
        {"fecha_de_corte": date(2026, 11, 6)},
        {"capital": "20000.01"},
        {"intereses": "720.01"},
        {"interes_corrido": "100.01"},
        {"en_revision": []},
        {"vencen_despues": []},
    ],
)
def test_la_huella_cambia_con_cada_parte_del_contenido(cambio: dict[str, object]) -> None:
    assert huella_del_certificado(_contenido(**cambio)) != huella_del_certificado(_contenido())


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("0.00", "0,00"),
        ("20720.00", "20.720,00"),
        ("1234567.89", "1.234.567,89"),
        ("-5.00", "-5,00"),
    ],
)
def test_los_montos_del_pdf_van_con_punto_de_miles_y_coma(texto: str, esperado: str) -> None:
    assert monto_para_el_pdf(texto) == esperado


@pytest.mark.parametrize("malo", ["20720", "20720.0", "1e3", "", "20.720,00"])
def test_un_monto_mal_formado_frena_el_pdf(malo: str) -> None:
    with pytest.raises(ValueError, match="monto"):
        monto_para_el_pdf(malo)


def test_la_leyenda_libre_de_deuda_sale_sólo_con_saldo_cero() -> None:
    con_deuda = _html(_contenido()).lower()
    libre = _html(_contenido(capital="0.00", intereses="0.00", en_revision=[], vencen_despues=[]))
    assert "libre de deuda" not in con_deuda
    assert "libre de deuda" in libre.lower() and "0,00" in libre


def test_el_html_escapa_lo_que_viene_del_pago() -> None:
    html = _html(_contenido())
    assert "Banco &lt;Nación&gt;" in html and "Banco <Nación>" not in html
    assert "10.000,00" in html and "05/11/2026" in html


def test_el_enlace_firmado_es_de_tipo_libre_deuda_y_vence() -> None:
    admin, certificado = uuid4(), uuid4()
    ahora = datetime.now(UTC)
    token = firmar_enlace(
        administracion_id=admin,
        certificado_id=certificado,
        vence_en=ahora + timedelta(minutes=15),
        clave=CLAVE,
    )
    enlace = verificar_enlace(token, clave=CLAVE, ahora=ahora)
    assert (enlace.administracion_id, enlace.certificado_id) == (admin, certificado)
    with pytest.raises(EnlaceVencido):
        verificar_enlace(token, clave=CLAVE, ahora=ahora + timedelta(minutes=16))
    with pytest.raises(EnlaceAlterado):
        verificar_enlace(token[:-1] + ("0" if token[-1] != "0" else "1"), clave=CLAVE, ahora=ahora)


def test_un_token_de_otro_tipo_o_sin_los_datos_no_sirve() -> None:
    vence = datetime.now(UTC) + timedelta(minutes=5)
    de_expensa = firmar(
        "expensa", {"a": str(uuid4()), "i": str(uuid4())}, vence_en=vence, clave=CLAVE
    )
    with pytest.raises(EnlaceAlterado):
        verificar_enlace(de_expensa, clave=CLAVE, ahora=datetime.now(UTC))
    sin_datos = firmar("libre_deuda", {"a": "no-es-uuid"}, vence_en=vence, clave=CLAVE)
    with pytest.raises(EnlaceAlterado):
        verificar_enlace(sin_datos, clave=CLAVE, ahora=datetime.now(UTC))
