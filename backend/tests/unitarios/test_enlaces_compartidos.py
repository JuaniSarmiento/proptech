"""La firma compartida de los enlaces (8, H-024, E1): el tipo va dentro del cuerpo firmado."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from proptech_core.compartido.enlaces import (
    EnlaceAlterado,
    EnlaceVencido,
    firmar,
    verificar,
)

CLAVE = "clave-de-prueba-de-enlaces-firmados-0123456789"
AHORA = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
VENCE = AHORA + timedelta(minutes=15)


def test_un_token_se_verifica_con_su_tipo_y_devuelve_lo_firmado() -> None:
    adm, pago = uuid4(), uuid4()
    token = firmar("comprobante", {"a": str(adm), "p": str(pago)}, vence_en=VENCE, clave=CLAVE)
    datos = verificar(token, tipo="comprobante", clave=CLAVE, ahora=AHORA)
    assert datos["a"] == str(adm)
    assert datos["p"] == str(pago)
    assert datos["e"] == int(VENCE.timestamp())


def test_un_token_de_un_tipo_no_se_verifica_como_otro() -> None:
    token = firmar("expensa", {"a": str(uuid4())}, vence_en=VENCE, clave=CLAVE)
    with pytest.raises(EnlaceAlterado):
        verificar(token, tipo="comprobante", clave=CLAVE, ahora=AHORA)


def test_el_tipo_no_se_puede_cambiar_sin_romper_la_firma() -> None:
    token = firmar("expensa", {"a": str(uuid4())}, vence_en=VENCE, clave=CLAVE)
    otro = firmar("comprobante", {"a": str(uuid4())}, vence_en=VENCE, clave=CLAVE)
    mezclado = otro.split(".")[0] + "." + token.split(".")[1]
    with pytest.raises(EnlaceAlterado):
        verificar(mezclado, tipo="comprobante", clave=CLAVE, ahora=AHORA)


def test_vencido_y_alterado_son_fallos_distintos() -> None:
    token = firmar("comprobante", {"a": str(uuid4())}, vence_en=VENCE, clave=CLAVE)
    with pytest.raises(EnlaceVencido):
        verificar(token, tipo="comprobante", clave=CLAVE, ahora=VENCE)
    with pytest.raises(EnlaceAlterado):
        verificar(
            token[:-1] + ("0" if token[-1] != "0" else "1"),
            tipo="comprobante",
            clave=CLAVE,
            ahora=AHORA,
        )
    with pytest.raises(EnlaceAlterado):
        verificar("basura", tipo="comprobante", clave=CLAVE, ahora=AHORA)


def test_clave_corta_y_vencimiento_sin_zona_se_rechazan() -> None:
    with pytest.raises(ValueError, match="clave"):
        firmar("comprobante", {}, vence_en=VENCE, clave="corta")
    with pytest.raises(ValueError, match="zona"):
        firmar("comprobante", {}, vence_en=datetime(2026, 11, 18, 12, 0), clave=CLAVE)
