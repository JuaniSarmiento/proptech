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
        "cuenta_corriente": {"umbral_saldo_chico": "500.00"},
        "invitaciones": {"vencimiento_dias": 7},
        "intereses": {
            "tasa_mensual": "3.00",
            "dias_de_gracia": 0,
            "forma_de_calculo": "proporcional_por_dia",
        },
        "fondo_de_reserva": {"porcentaje": "0.00"},
        "vencimiento": {
            "dia": 10,
            "modalidad": "unico",
            "rango_recargo": {"minimo": "0.01", "maximo": "20.00"},
        },
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


# --- D13 (deuda del 1b con dueño 3, tarea 2.3, L-009): el gemelo de los dos
# lectores. `_validador_porcentaje` (tasa_mensual, fondo_de_reserva, factor)
# y `superficie_m2` ahora delegan el formato en `Porcentaje`/`Superficie`
# (compartido/), así que un sufijo peligroso tiene que fallar en los dos
# lectores con el mismo mecanismo, no sólo en el tipo nuevo aislado. No es
# un rojo nuevo (ya lo demuestran `test_porcentaje.py` y `test_superficie.py`
# contra el tipo directo, y el de arriba contra `_PATRON_COEFICIENTE`); queda
# como guarda de que la batería llega hasta los dos lectores, no sólo hasta
# el tipo. ---


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_factor_de_estado_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.parametros import Parametros

    datos = _parametros_validos()
    datos["estados_de_unidad"]["estados"][0]["factor"] = "100.00" + sufijo
    with pytest.raises(ValidationError):
        Parametros(**datos)


@pytest.mark.parametrize("sufijo", _SUFIJOS_PELIGROSOS)
def test_superficie_m2_rechaza_sufijo_peligroso(sufijo: str) -> None:
    from pydantic import ValidationError

    from proptech_core.compartido.semilla import Unidad

    with pytest.raises(ValidationError):
        Unidad(
            identificador="1A",
            tipo="departamento",
            piso="1",
            coeficiente="0.400000",  # type: ignore[arg-type]
            superficie_m2="60.00" + sufijo,  # type: ignore[arg-type]
        )
