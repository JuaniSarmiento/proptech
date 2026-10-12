"""Regresion (rompedor, cambio 1b vuelta 2): `cargar_yaml` (D6) promete que un
YAML mal formado falla con un `ErrorDeCarga` controlado ("sin traza ni
contenido"), nunca con una excepción sin capturar. Un archivo chico pero muy
anidado (listas dentro de listas) agota la pila de recursión de PyYAML/Python
antes de que el parser termine: el resultado era un `RecursionError` sin
capturar, con traceback completo, que además se propagaba sin control a
través de `leer_parametros` y `leer_semilla` (ambas sólo atrapaban
`ErrorDeCarga`) hasta quien llame al lector — en producción, hasta el
arranque de la API o el comando de verificación de la semilla. Arreglado
capturando `RecursionError`/`MemoryError` en `cargar_yaml` (más un límite de
tamaño de archivo, ver design.md); estos tests quedan como regresión.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Suficiente para superar el límite de recursión de Python (1000 por default)
# incluso contando los frames propios del parser/constructor de PyYAML, pero
# un archivo de poquísimos KB: no hace falta un archivo "grande" para tirar
# abajo el proceso.
_PROFUNDIDAD = 3000


def _yaml_muy_anidado(profundidad: int) -> bytes:
    return b"root: " + b"[" * profundidad + b"1" + b"]" * profundidad


def test_yaml_muy_anidado_no_debe_crashear_con_recursionerror() -> None:
    from proptech_core.compartido.cargador_yaml import ErrorDeCarga, cargar_yaml

    contenido = _yaml_muy_anidado(_PROFUNDIDAD)
    assert len(contenido) < 20_000, "el archivo que rompe el parser es chico, no gigante"

    with pytest.raises(ErrorDeCarga):
        # Antes del fix esto levantaba RecursionError (no ErrorDeCarga): un
        # archivo de ~6 KB tiraba abajo el proceso que lo estuviera leyendo
        # con una excepción sin controlar, en vez del error prolijo que
        # promete la spec.
        cargar_yaml(contenido)


def test_parametros_con_yaml_muy_anidado_no_debe_crashear_el_proceso(tmp_path: Path) -> None:
    """La misma falla, por el camino que de verdad usa la API: `leer_parametros`
    sólo atrapa `ErrorDeCarga`, así que antes del fix un `PROPTECH_PARAMETROS`
    apuntando a un archivo así tiraba abajo el arranque con un `RecursionError`
    en vez de la `ParametrosInvalidos` prolija que exige la spec."""
    from proptech_core.compartido.parametros import ParametrosInvalidos, leer_parametros

    ruta = tmp_path / "parametros_anidado.yaml"
    ruta.write_bytes(_yaml_muy_anidado(_PROFUNDIDAD))

    with pytest.raises(ParametrosInvalidos):
        leer_parametros(str(ruta))
