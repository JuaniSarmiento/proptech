"""Regresión (auditor, cambio 1b vuelta 3): dos incumplimientos de SHALL de
`specs/datos-semilla/spec.md` ("Semilla validada contra los parámetros"), que
exige rechazar "coeficientes que no son texto decimal positivo" e
"identificadores de unidad repetidos" **nombrando el campo y la unidad**.

1. `_coeficiente_valido` (semilla.py) sólo validaba el *formato* (hasta 6
   decimales, un dígito entero) y nunca la *positividad*: "0.000000" pasaba el
   patrón y quedaba como un coeficiente válido, pese a que la spec pide texto
   decimal **positivo**.
2. `_validar_contra_parametros` reportaba "unidades: hay un identificador
   repetido" sin decir cuál, al revés de lo que exige la spec.

Arreglado: `_coeficiente_valido` ahora rechaza `<= 0` después de validar el
formato; `_validar_contra_parametros` nombra los identificadores duplicados.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

#: 6.5: mismos ids reales que `tests/integracion/_georef_real.py`
#: (Mendoza/Capital/"Mendoza"), 4 pisos y 1 subsuelo — para que el único
#: problema de cada caso sea el que el test provoca a propósito.
BASE: dict[str, Any] = {
    "version": 1,
    "edificio": {
        "nombre": "Edificio Ejemplo",
        "provincia_id": "50",
        "departamento_id": "50007",
        "localidad_id": "50007010",
        "pisos": 4,
        "subsuelos": 1,
        "estado_migracion": "sin_saldos_previos",
    },
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
            "piso": "SS1",
            "coeficiente": "0.300000",
            "superficie_m2": "12.50",
        },
    ],
    "grupos": {
        "generales": "todas",
        "cocheras": ["C1"],
    },
}


@pytest.fixture
def parametros() -> Any:
    from proptech_core.compartido.parametros import leer_parametros

    raiz = Path(__file__).resolve().parents[3]
    return leer_parametros(str(raiz / "config" / "parametros.yaml"))


@pytest.fixture
def georef() -> Any:
    from proptech_core.compartido.georef import leer_georef

    raiz = Path(__file__).resolve().parents[3]
    return leer_georef(str(raiz / "config" / "georef"))


def _valido() -> dict[str, Any]:
    return copy.deepcopy(BASE)


def _dump(datos: dict[str, Any]) -> bytes:
    return yaml.safe_dump(datos, allow_unicode=True).encode()


def _escribir_y_leer(datos: dict[str, Any], parametros: Any, georef: Any, tmp_path: Path) -> None:
    from proptech_core.compartido.semilla import leer_semilla

    ruta = tmp_path / "semilla.yaml"
    ruta.write_bytes(_dump(datos))
    leer_semilla(str(ruta), parametros, georef)


def test_coeficiente_cero_falla_por_no_ser_positivo(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    """La suma se compensa en otra unidad (sigue dando exactamente 1) para
    que el único problema posible sea la positividad del coeficiente, no la
    suma: así el test no puede pasar "de rebote" por el chequeo de suma."""
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    datos["unidades"][0]["coeficiente"] = "0.000000"
    datos["unidades"][1]["coeficiente"] = "0.700000"
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    assert "unidades[0].coeficiente" in str(exc_info.value)


def test_identificador_repetido_nombra_el_identificador(
    parametros: Any, georef: Any, tmp_path: Path
) -> None:
    from proptech_core.compartido.semilla import SemillaInvalida

    datos = _valido()
    repetido = datos["unidades"][0]["identificador"]
    datos["unidades"][1]["identificador"] = repetido
    with pytest.raises(SemillaInvalida) as exc_info:
        _escribir_y_leer(datos, parametros, georef, tmp_path)
    mensaje = str(exc_info.value)
    assert "unidades" in mensaje
    assert repetido in mensaje
