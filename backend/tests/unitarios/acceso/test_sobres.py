"""D6: sobre autenticado, vencimiento y resumen sin texto en claro."""

import base64
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr


def test_sobre_no_transporta_token_y_rechaza_manipulacion() -> None:
    from proptech_core.acceso.dominio.sobres import SobreInvalido, abrir, generar

    clave = SecretStr(base64.b64encode(b"c" * 32).decode())
    ahora = datetime(2026, 10, 21, tzinfo=UTC)
    resumen, sobre = generar(clave, ahora + timedelta(days=7))
    crudo = abrir(clave, sobre, ahora)
    assert hashlib.sha256(crudo.encode()).digest() == resumen
    assert crudo not in sobre and resumen.hex() not in sobre
    datos = bytearray(base64.urlsafe_b64decode(sobre + "=" * (-len(sobre) % 4)))
    for indice in (0, 4, 12, len(datos) - 1):
        alterado = datos.copy()
        alterado[indice] ^= 1
        with pytest.raises(SobreInvalido):
            abrir(clave, base64.urlsafe_b64encode(alterado).decode().rstrip("="), ahora)
    with pytest.raises(SobreInvalido):
        abrir(clave, sobre, ahora + timedelta(days=7))


def test_parametro_de_vencimiento_estricto() -> None:
    import copy

    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros
    from tests.unitarios.test_parametros import BASE

    for valor in (0, -1, True, "7", 7.5):
        datos = copy.deepcopy(BASE)
        datos["invitaciones"] = {"vencimiento_dias": valor}
        with pytest.raises(ValidationError):
            Parametros(**datos)
    datos = copy.deepcopy(BASE)
    datos["invitaciones"] = {"vencimiento_dias": 7}
    assert Parametros(**datos).invitaciones.vencimiento_dias == 7
