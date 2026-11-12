"""Tarea 1.5 de `importacion-desde-excel`: de las filas validadas a las personas únicas (design D4,
E3). Puro: sin base. Datos inventados.

Decisión de la tanda 2 (el relevo de 1.3 la dejó abierta): un email repetido en dos filas con otro
nombre es **la misma persona**, se queda con el nombre de la primera fila y la segunda fila suma una
advertencia (hoja `Unidades`, su fila, columna `Propietario`). No es error: el mismo email es la
misma persona (contrato de H-007) y rechazar el archivo por un nombre escrito distinto sería duro.
"""

from __future__ import annotations

from proptech_core.compartido.coeficientes import Coeficiente
from proptech_core.compartido.superficie import Superficie
from proptech_core.importacion.dominio.padron import UnidadAImportar
from proptech_core.importacion.dominio.propietarios import agrupar_propietarios


def _unidad(fila: int, propietario: str | None, email: str | None) -> UnidadAImportar:
    return UnidadAImportar(
        fila=fila,
        identificador=f"U{fila}",
        tipo="departamento",
        piso="1",
        coeficiente=Coeficiente("0.100000"),
        superficie_m2=Superficie("50.00"),
        propietario=propietario,
        email=email,
    )


def test_sin_propietarios_no_hay_personas() -> None:
    plan = agrupar_propietarios((_unidad(2, None, None), _unidad(3, None, None)))
    assert plan.personas == {}
    assert plan.advertencias == ()


def test_el_mismo_email_en_dos_filas_es_una_sola_persona() -> None:
    plan = agrupar_propietarios(
        (
            _unidad(2, "Persona Ficticia Uno", "uno@ficticio.test"),
            _unidad(3, "Persona Ficticia Uno", "uno@ficticio.test"),
            _unidad(4, "Persona Ficticia Dos", "dos@ficticio.test"),
        )
    )
    assert plan.personas == {
        "uno@ficticio.test": "Persona Ficticia Uno",
        "dos@ficticio.test": "Persona Ficticia Dos",
    }
    assert plan.advertencias == ()


def test_el_mismo_email_con_otro_nombre_conserva_el_primero_y_advierte() -> None:
    plan = agrupar_propietarios(
        (
            _unidad(2, "Persona Ficticia Uno", "uno@ficticio.test"),
            _unidad(5, "P. Ficticia 1", "uno@ficticio.test"),
        )
    )
    assert plan.personas == {"uno@ficticio.test": "Persona Ficticia Uno"}
    assert len(plan.advertencias) == 1
    aviso = plan.advertencias[0]
    assert (aviso.hoja, aviso.fila, aviso.columna) == ("Unidades", 5, "Propietario")
    assert "fila 2" in aviso.motivo
    assert "uno@ficticio.test" not in aviso.motivo, "el motivo no repite el valor escrito"


def test_los_propietarios_sin_email_no_se_agrupan() -> None:
    plan = agrupar_propietarios(
        (_unidad(2, "Persona Ficticia Uno", None), _unidad(3, "Persona Ficticia Uno", None))
    )
    assert plan.personas == {}
    assert plan.advertencias == ()
