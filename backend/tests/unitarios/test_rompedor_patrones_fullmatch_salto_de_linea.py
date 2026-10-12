"""Regresión (auditor, cambio 1b vuelta 3), familia completa de L-002: todo
patrón que valida texto externo con `^...$` y `.match()` acepta un salto de
línea final, porque en Python `$` matchea antes de un `\\n` final del string
(sin `re.MULTILINE`) y `Decimal()`/el valor construido ignora ese sobrante.
Afecta a los cuatro puntos de entrada de texto de dominio del cambio: `Dinero`
(dinero.py), `_validador_porcentaje` compartido por `tasa_mensual` y
`fondo_de_reserva.porcentaje` (parametros.py), `_PATRON_COEFICIENTE`
(semilla.py) y `_PATRON_CLAVE` (parametros.py, usado por toda `clave` del
esquema). Arreglado cambiando `.match()` por `.fullmatch()` (con `re.ASCII`
también en `_PATRON_CLAVE`, por consistencia aunque hoy no use `\\d`) en los
cuatro. Se prueban además `\\r`, `\\t`, un espacio y un byte NUL, antes y
después del texto válido, para no cerrar sólo el caso del salto de línea.
"""

from __future__ import annotations

from typing import Any

import pytest

_SUFIJOS_PELIGROSOS = ["\n", "\r", "\t", " ", "\x00"]
_PREFIJOS_PELIGROSOS = ["\n", "\r", "\t", " ", "\x00"]


def _parametros_validos() -> dict[str, Any]:
    return {
        "version": 1,
        "intereses": {
            "tasa_mensual": "3.00",
            "dias_de_gracia": 0,
            "forma_de_calculo": "proporcional_por_dia",
        },
        "fondo_de_reserva": {"porcentaje": "0.00"},
        "categorias_de_gasto": [{"clave": "encargado", "nombre": "Encargado"}],
        "grupos_de_reparto": [
            {
                "clave": "generales",
                "nombre": "Generales",
                "metodo": "coeficiente",
                "alcance": "todas_las_unidades",
            }
        ],
        "tipos_de_unidad": [{"clave": "departamento", "nombre": "Departamento"}],
        "estados_de_unidad": {
            "habilitados": False,
            "estados": [{"clave": "x", "nombre": "X", "factor": "100.00", "cargo_fijo": "0.00"}],
        },
    }


# --- Dinero (D5, dinero.py) ---


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_dinero_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero("1.00" + sufijo)


@pytest.mark.parametrize("prefijo", _PREFIJOS_PELIGROSOS)
def test_dinero_rechaza_prefijo_peligroso(prefijo: str) -> None:
    from proptech_core.compartido.dinero import Dinero, MontoInvalido

    with pytest.raises(MontoInvalido):
        Dinero(prefijo + "1.00")


# --- tasa_mensual / fondo_de_reserva.porcentaje (D6, parametros.py) ---


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_tasa_mensual_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _parametros_validos()
    datos["intereses"]["tasa_mensual"] = "3.00" + sufijo
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_fondo_de_reserva_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _parametros_validos()
    datos["fondo_de_reserva"]["porcentaje"] = "0.00" + sufijo
    with pytest.raises(ValidationError):
        Parametros(**datos)


# --- clave (D6, parametros.py, _PATRON_CLAVE) ---


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_clave_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _parametros_validos()
    datos["categorias_de_gasto"][0]["clave"] = "encargado" + sufijo
    with pytest.raises(ValidationError):
        Parametros(**datos)


# --- coeficiente (D10, semilla.py, _PATRON_COEFICIENTE) ---


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_coeficiente_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.semilla import Unidad

    with pytest.raises(ValidationError):
        Unidad(
            identificador="1A",
            tipo="departamento",
            piso="1",
            coeficiente="0.400000" + sufijo,  # type: ignore[arg-type]
            superficie_m2="60.00",  # type: ignore[arg-type]
        )
