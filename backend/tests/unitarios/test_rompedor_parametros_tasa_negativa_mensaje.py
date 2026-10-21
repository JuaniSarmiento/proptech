"""Regresion (rompedor, cambio 1b vuelta 2): el escenario "Tasa negativa" de
`specs/parametros-del-sistema/spec.md` exige que, con `tasa_mensual: "-1.00"`,
"el lector falla nombrando `intereses.tasa_mensual` **y el rango permitido**".

`_PATRON_PORCENTAJE` (`^\\d{1,3}(\\.\\d{1,2})?$`) no admite el signo `-`, así
que un valor negativo nunca llegaba al chequeo de rango (`0 a 10`): reventaba
antes, en el chequeo de formato, con el mensaje "formato inválido: hasta 2
decimales, sin signo". El campo aparecía nombrado, pero el rango permitido
(0 y 10) nunca se mencionaba, al revés de lo que pide el escenario. El test
existente (`test_tasa_fuera_de_rango_o_mal_formada_falla`, que agrupa
"-1.00", "10.01" y "3.005") sólo verifica que levante `ValidationError`, sin
mirar el texto del mensaje: no cubría este camino. Arreglado agregando el
rango al mensaje de formato de `_validador_porcentaje` (`parametros.py`),
compartido por tasa y fondo de reserva; este test queda como regresión.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


def _parametros_validos() -> dict[str, Any]:
    return {
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
            "estados": [
                {"clave": "baldio", "nombre": "Baldío", "factor": "100.00", "cargo_fijo": "0.00"}
            ],
        },
    }


def test_tasa_negativa_nombra_el_rango_permitido(tmp_path: Path) -> None:
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    datos = _parametros_validos()
    datos["intereses"]["tasa_mensual"] = "-1.00"
    ruta = tmp_path / "parametros.yaml"
    ruta.write_bytes(yaml.safe_dump(datos).encode())

    with pytest.raises(ParametrosInvalidos) as exc_info:
        leer_parametros(str(ruta))

    mensaje = str(exc_info.value)
    assert "intereses.tasa_mensual" in mensaje
    # El escenario "Tasa negativa" de la spec exige que el mensaje nombre el
    # rango permitido (0 a 10), no sólo el campo. Hoy dice "sin signo" y
    # nunca llega a mencionar el rango.
    assert "0" in mensaje and "10" in mensaje, (
        f"el mensaje debía nombrar el rango permitido (0 a 10); fue: {mensaje!r}"
    )
