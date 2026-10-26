"""D-114.6 y D10: fijaciones que se vigilan con mutantes dirigidos."""

from decimal import Decimal
from pathlib import Path

import pytest

from proptech_core.compartido.dinero import Dinero, MontoInvalido
from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros
from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla


@pytest.mark.parametrize("lector", ["parametros", "semilla"])
@pytest.mark.parametrize("contenido", ["- MARCADOR_PRIVADO", "12345: MARCADOR_PRIVADO"])
def test_yaml_corta_raiz_y_claves_sin_valores(tmp_path: Path, lector: str, contenido: str) -> None:
    ruta = tmp_path / "entrada.yaml"
    ruta.write_text(contenido)
    error = ParametrosInvalidos if lector == "parametros" else SemillaInvalida
    capturado: Exception | None = None
    try:
        if lector == "parametros":
            leer_parametros(str(ruta))
        else:
            ruta_parametros = Path(__file__).resolve().parents[3] / "config/parametros.yaml"
            parametros = leer_parametros(str(ruta_parametros))
            leer_semilla(str(ruta), parametros)
    except Exception as obtenido:
        capturado = obtenido
    mensaje = f"se esperaba {error.__name__}, se obtuvo {type(capturado).__name__}"
    assert isinstance(capturado, error), mensaje
    assert "MARCADOR_PRIVADO" not in str(capturado)
    assert "Traceback" not in str(capturado)
    assert capturado.__suppress_context__ is True


@pytest.mark.parametrize("valor,esperado", [("1.0000", "1.00"), ("0.3000", "0.30")])
def test_decimal_con_ceros_conserva_valor(valor: str, esperado: str) -> None:
    assert Dinero.desde_decimal(Decimal(valor)).a_texto() == esperado


@pytest.mark.parametrize("valor", ["1.005", "1.0001"])
def test_decimal_que_cambiaria_no_se_redondea(valor: str) -> None:
    with pytest.raises(MontoInvalido):
        Dinero.desde_decimal(Decimal(valor))


@pytest.mark.parametrize("valor", ["1.0000", "1.000"])
def test_texto_con_ceros_sobrantes_se_rechaza(valor: str) -> None:
    with pytest.raises(MontoInvalido):
        Dinero(valor)
