"""`PROPTECH_CLAVE_DE_ENLACES` (7, H-015, D-070): la clave que firma los enlaces de descarga."""

import pytest
from pydantic import SecretStr

from proptech_core.compartido.configuracion import Configuracion, ConfiguracionInvalida

CLAVE = "clave-de-prueba-de-enlaces-firmados-0123456789"


@pytest.fixture(autouse=True)
def sin_clave(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROPTECH_CLAVE_DE_ENLACES", raising=False)


def test_sin_la_variable_no_se_firman_enlaces_pero_el_sistema_arranca() -> None:
    config = Configuracion()
    assert config.proptech_clave_de_enlaces is None
    with pytest.raises(ConfiguracionInvalida, match="PROPTECH_CLAVE_DE_ENLACES"):
        config.clave_de_enlaces()


def test_configurada_se_oculta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPTECH_CLAVE_DE_ENLACES", CLAVE)
    config = Configuracion()
    assert isinstance(config.proptech_clave_de_enlaces, SecretStr)
    assert config.clave_de_enlaces() == CLAVE
    for representacion in (repr(config), str(vars(config)), repr(config.proptech_clave_de_enlaces)):
        assert CLAVE not in representacion


@pytest.mark.parametrize("valor", ["", "   ", "corta", "x" * 31, f" {CLAVE}", f"{CLAVE}\n"])
def test_una_clave_corta_o_con_espacios_se_rechaza_sin_mostrar_su_valor(
    monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    monkeypatch.setenv("PROPTECH_CLAVE_DE_ENLACES", valor)
    with pytest.raises(ConfiguracionInvalida) as error:
        Configuracion()
    assert "PROPTECH_CLAVE_DE_ENLACES" in str(error.value)
    if valor.strip():
        assert valor.strip() not in str(error.value)
