"""Regresión (constructor, cambio 1b vuelta 4): una clave de YAML que no es
texto (un entero, por ejemplo) escapaba de maneras distintas según quién la
leyera.

En `leer_parametros`, `Parametros(**datos)` levantaba un `TypeError` crudo
("keywords must be strings") que quedaba envuelto a mano en
`ParametrosInvalidos` — pero con el texto de la excepción de Python, no con
una descripción propia. En `leer_semilla` el mismo caso ni se atrapaba: el
`TypeError` de `Semilla(**datos)` escapaba sin control hasta quien llamara
(el comando de la semilla, con traceback incluido). L-009 exige que el
arreglo cierre la familia en los dos lectores, no sólo en uno; se corrige una
sola vez, en `cargar_yaml`, para que ninguno de los dos vea nunca una clave
no-texto. El chequeo corre para la raíz y para cualquier mapa anidado, porque
es el mismo constructor el que arma todos los niveles.

El mensaje nombra la posición (línea y columna) y el tipo recibido, nunca el
valor de la clave ni el de su valor asociado (motivo de esta vuelta: "sin
filtrar valores")."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

_SECRETO = "SECRETO-ABC"

_PARAMETROS_VALIDOS: dict[str, Any] = {
    "version": 1,
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


def test_cargar_yaml_rechaza_clave_no_texto_en_la_raiz() -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    contenido = f"1: {_SECRETO}\n".encode()

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(contenido)

    mensaje = str(exc_info.value)
    assert _SECRETO not in mensaje
    assert any(c.isdigit() for c in mensaje)


def test_cargar_yaml_rechaza_clave_no_texto_anidada() -> None:
    """Cierra la familia (L-009): el mismo defecto, un nivel más adentro."""
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    contenido = f"raiz:\n  2: {_SECRETO}\n".encode()

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(contenido)

    assert _SECRETO not in str(exc_info.value)


def test_cargar_yaml_rechaza_clave_booleana() -> None:
    """`true`/`false` también resuelven a un tipo que no es texto."""
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    with pytest.raises(ErrorDeCarga):
        cargar_yaml(b"true: 1\n")


def test_leer_parametros_con_clave_no_texto_en_la_raiz_falla_sin_traceback(
    tmp_path: Path,
) -> None:
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    ruta = tmp_path / "parametros.yaml"
    ruta.write_text(f"1: {_SECRETO}\nversion: 1\n")

    with pytest.raises(ParametrosInvalidos) as exc_info:
        leer_parametros(str(ruta))

    assert _SECRETO not in str(exc_info.value)


def test_leer_semilla_con_clave_no_texto_en_la_raiz_falla_sin_traceback(tmp_path: Path) -> None:
    """Antes de este arreglo, este caso no estaba atajado en absoluto: un
    `TypeError` de pydantic escapaba sin control de `leer_semilla` (L-009)."""
    from proptech_core.compartido.parametros import Parametros
    from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla

    parametros = Parametros(**_PARAMETROS_VALIDOS)

    ruta = tmp_path / "semilla.yaml"
    ruta.write_text(f"1: {_SECRETO}\nversion: 1\n")

    with pytest.raises(SemillaInvalida) as exc_info:
        leer_semilla(str(ruta), parametros)

    assert _SECRETO not in str(exc_info.value)
