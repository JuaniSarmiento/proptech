from pathlib import Path
from typing import Any

import pytest
import yaml

from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

REPO = Path(__file__).resolve().parents[3] / "config/parametros.yaml"


def test_umbral_del_repo() -> None:
    assert leer_parametros(str(REPO)).cuenta_corriente.umbral_saldo_chico.a_texto() == "500.00"


@pytest.mark.parametrize("valor", [None, "", " ", "-0.01", "1.001", 500, " 500.00", "500.00\n"])
def test_umbral_invalido(tmp_path: Path, valor: Any) -> None:
    datos = yaml.safe_load(REPO.read_text())
    datos["cuenta_corriente"] = {} if valor is None else {"umbral_saldo_chico": valor}
    archivo = tmp_path / "parametros.yaml"
    archivo.write_text(yaml.safe_dump(datos))
    with pytest.raises(ParametrosInvalidos) as error:
        leer_parametros(str(archivo))
    assert "cuenta_corriente.umbral_saldo_chico" in str(error.value)
    if isinstance(valor, str) and valor.strip():
        assert valor not in str(error.value)


def test_umbral_cero(tmp_path: Path) -> None:
    datos = yaml.safe_load(REPO.read_text())
    datos["cuenta_corriente"] = {"umbral_saldo_chico": "0.00"}
    archivo = tmp_path / "parametros.yaml"
    archivo.write_text(yaml.safe_dump(datos))
    assert leer_parametros(str(archivo)).cuenta_corriente.umbral_saldo_chico.a_texto() == "0.00"
