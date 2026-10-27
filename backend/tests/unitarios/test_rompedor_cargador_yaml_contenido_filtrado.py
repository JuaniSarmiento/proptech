"""Regresión (auditor, cambio 1b vuelta 3): `cargar_yaml` armaba el mensaje de
`yaml.YAMLError` con `f"...: {error}"`. `str(error)` en PyYAML incluye el
snippet de la línea que rompió el parseo (el texto exacto con un `^` marcando
la columna), así que un `tasa_mensual: "SECRETO-ABC` mal cerrado filtraba
"SECRETO-ABC" en el mensaje de `ErrorDeCarga`, y `leer_parametros` /
`leer_semilla` lo reenvían tal cual con `str(error)`. La spec
(specs/parametros-del-sistema, "El error de formato no filtra el archivo")
exige que el error "MUST NOT incluir el contenido del archivo" y que sea
"sin traza ni contenido": D13 decía que ya estaba así, y no era cierto para
este camino. Arreglado: el mensaje nombra sólo la posición (línea y columna)
y una descripción genérica, nunca el texto que devuelve PyYAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

_SECRETO = "SECRETO-ABC"

_PARAMETROS_VALIDOS: dict[str, Any] = {
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


def test_cargar_yaml_no_filtra_contenido_del_archivo_roto() -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    contenido = f'tasa_mensual: "{_SECRETO}\n'.encode()

    with pytest.raises(ErrorDeCarga) as exc_info:
        cargar_yaml(contenido)

    mensaje = str(exc_info.value)
    assert _SECRETO not in mensaje
    assert "mal formado" in mensaje.lower()


def test_leer_parametros_no_filtra_contenido_del_archivo_roto(tmp_path: Path) -> None:
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    ruta = tmp_path / "parametros.yaml"
    ruta.write_text(f'intereses:\n  tasa_mensual: "{_SECRETO}\n')

    with pytest.raises(ParametrosInvalidos) as exc_info:
        leer_parametros(str(ruta))

    assert _SECRETO not in str(exc_info.value)


def test_leer_semilla_no_filtra_contenido_del_archivo_roto(tmp_path: Path) -> None:
    from proptech_core.compartido.georef import Georef
    from proptech_core.compartido.parametros import Parametros
    from proptech_core.compartido.semilla import SemillaInvalida, leer_semilla

    parametros = Parametros(**_PARAMETROS_VALIDOS)
    georef = Georef(provincias=(), departamentos=(), localidades=())

    ruta = tmp_path / "semilla.yaml"
    ruta.write_text(f'edificio:\n  nombre: "{_SECRETO}\n')

    with pytest.raises(SemillaInvalida) as exc_info:
        leer_semilla(str(ruta), parametros, georef)

    assert _SECRETO not in str(exc_info.value)
