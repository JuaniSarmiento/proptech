"""5.1: leer_semilla (D10) — la semilla del edificio de ejemplo."""

import copy
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
PARAMETROS_PATH = RAIZ / "config" / "parametros.yaml"


@pytest.fixture
def parametros() -> Any:
    from proptech_core.compartido.parametros import leer_parametros

    return leer_parametros(str(PARAMETROS_PATH))


BASE: dict[str, Any] = {
    "version": 1,
    "edificio": {"nombre": "Edificio Ejemplo", "localidad": "Mendoza"},
    "unidades": [
        {
            "identificador": "L-PB",
            "tipo": "local",
            "piso": "PB",
            "coeficiente": "0.400000",
            "superficie_m2": "45.00",
        },
        {
            "identificador": "1A",
            "tipo": "departamento",
            "piso": "1",
            "coeficiente": "0.300000",
            "superficie_m2": "60.00",
        },
        {
            "identificador": "C1",
            "tipo": "cochera",
            "piso": "SS",
            "coeficiente": "0.300000",
            "superficie_m2": "12.50",
        },
    ],
    "grupos": {
        "generales": "todas",
        "cocheras": ["C1"],
    },
}


def _dump(datos: dict[str, Any]) -> bytes:
    return yaml.safe_dump(datos, allow_unicode=True).encode()


def _valido() -> dict[str, Any]:
    return copy.deepcopy(BASE)


def test_semilla_del_repo_es_valida_y_suma_exactamente_uno(parametros: Any) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml"
    semilla = leer_semilla(str(ruta), parametros)

    total = sum((u.coeficiente for u in semilla.unidades), start=Decimal(0))
    assert total == Decimal("1")


def test_base_de_test_es_valida(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(_valido()))
    semilla = leer_semilla(str(ruta), parametros)
    assert len(semilla.unidades) == 3


def _escribir_y_leer(datos: dict[str, Any], parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(datos))
    leer_semilla(str(ruta), parametros)


def test_tipo_desconocido_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["tipo"] = "quincho"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades[0].tipo" in str(exc_info.value)


def test_grupo_desconocido_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["grupos"]["no_existe"] = ["C1"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "grupos" in str(exc_info.value)
    assert "no_existe" in str(exc_info.value)


def test_identificador_repetido_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][1]["identificador"] = datos["unidades"][0]["identificador"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades" in str(exc_info.value)


def test_miembro_de_grupo_inexistente_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["grupos"]["cocheras"] = ["NO-EXISTE"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "cocheras" in str(exc_info.value)
    assert "NO-EXISTE" in str(exc_info.value)


def test_coeficiente_de_suma_distinta_de_uno_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "0.999999"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades" in str(exc_info.value)


def test_coeficiente_con_siete_decimales_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "0.4000001"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_coeficiente_como_numero_yaml_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = 0.4
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_coeficiente_con_digitos_no_ascii_falla(parametros: Any, tmp_path: Path) -> None:
    """Mismo problema que el rompedor encontró en `Dinero` y en
    `_PATRON_PORCENTAJE` (cambio 1b vuelta 2): `_PATRON_COEFICIENTE` usaba
    `\\d` sin `re.ASCII`, que matchea cualquier dígito Unicode de categoría
    Nd. Un coeficiente escrito con dígitos arábigo-índicos (equivalente a
    "0.400000") no debe aceptarse."""
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "٠.٤٠٠٠٠٠"  # noqa: RUF001 - "0.400000"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_superficie_no_positiva_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["superficie_m2"] = "0.00"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "unidades[0].superficie_m2" in str(exc_info.value)


def test_generales_distinto_de_todas_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["grupos"]["generales"] = ["C1"]
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, tmp_path)
    assert "generales" in str(exc_info.value)


def test_clave_duplicada_en_el_yaml_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_text("version: 1\nversion: 1\nedificio: {nombre: x, localidad: y}\n")
    with pytest.raises(SemillaInvalida):
        leer_semilla(str(ruta), parametros)


def test_campo_desconocido_falla(parametros: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["campo_extra"] = 1
    with pytest.raises(SemillaInvalida):
        _escribir_y_leer(datos, parametros, tmp_path)


def test_semilla_no_tiene_campos_de_persona_ni_contacto() -> None:
    """La semilla es ficticia: sin personas, sin contacto, sin calle (D10)."""
    import re

    texto = (RAIZ / "config" / "semilla" / "edificio-ejemplo.yaml").read_text()
    assert re.search(r"[\w.+-]+@[\w-]+\.\w+", texto) is None, "parece un email"
    assert re.search(r"\b\d{2,4}[-\s]?\d{6,8}\b", texto) is None, "parece un teléfono"
    for prohibida in ("nombre_completo", "dni", "telefono", "email", "contacto", "propietario"):
        assert prohibida not in texto.lower()
