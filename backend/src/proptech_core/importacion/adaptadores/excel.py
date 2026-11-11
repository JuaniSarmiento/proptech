"""Adaptador real de `LectorDePlantilla` (design D1, D2, D3, E9, E14): `openpyxl`, sólo lectura.

Qué hace de verdad la librería, probado en `tests/unitarios/test_importacion_lector_excel.py`
(L-066):

- Las hojas y los encabezados (fila 1) se buscan por nombre exacto: ni mayúsculas, ni espacios, ni
  posición. Las columnas extra se ignoran.
- Las fórmulas se leen por su valor en caché (`data_only=True`): `openpyxl` no evalúa nada. Una
  fórmula sin valor guardado (la guarda así un script, no Excel) deja la celda vacía en esa
  lectura, así que el libro se abre una segunda vez sin `data_only` sólo para reconocerla y
  marcarla en `formulas_sin_cache`.
- Ninguna celda pasa por `float`: una celda numérica se convierte con `Decimal(repr(valor))` y se
  escribe en notación fija (`8.3e-05` es `0.000083`). Los textos llegan exactos, sin recortar.
- Antes de abrir nada se mide el archivo (2 MiB) y por hoja se cuentan las filas con datos (2.000).
"""

from __future__ import annotations

import datetime
import io
from decimal import Decimal
from typing import Any

from openpyxl import load_workbook

from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    LIMITE_DE_BYTES,
    LIMITE_DE_FILAS,
    ArchivoInvalido,
    ErrorDeImportacion,
    FilaLeida,
    HojaLeida,
    PlantillaLeida,
)

_MIB = 1024 * 1024


def _texto_de_celda(valor: Any) -> str | None:
    """La celda como texto exacto o `None` si está vacía; nunca un `float`."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "VERDADERO" if valor else "FALSO"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        exacto = Decimal(repr(valor))
        return format(exacto, "f") if exacto.is_finite() else repr(valor)
    if isinstance(valor, Decimal):
        return format(valor, "f") if valor.is_finite() else str(valor)
    if isinstance(valor, datetime.datetime):
        solo_fecha = valor.time() == datetime.time(0, 0)
        return valor.date().isoformat() if solo_fecha else valor.isoformat()
    if isinstance(valor, (datetime.date, datetime.time)):
        return valor.isoformat()
    texto = str(valor)
    return texto or None


def _no_es_un_excel(nombre: str | None) -> ArchivoInvalido:
    sujeto = f"El archivo {nombre!r}" if nombre else "El archivo"
    return ArchivoInvalido(
        [ErrorDeImportacion(None, None, None, f"{sujeto} no es un Excel (.xlsx) válido")]
    )


def _demasiado_grande(nombre: str | None) -> ArchivoInvalido:
    sujeto = f"El archivo {nombre!r}" if nombre else "El archivo"
    return ArchivoInvalido(
        [ErrorDeImportacion(None, None, None, f"{sujeto} supera el límite de 2 MiB")]
    )


def _demasiadas_filas(hoja: str) -> ArchivoInvalido:
    return ArchivoInvalido(
        [
            ErrorDeImportacion(
                hoja, None, None, f"La hoja {hoja} supera el límite de 2.000 filas de datos"
            )
        ]
    )


def _celda(fila: Any, posicion: int) -> Any:
    return fila[posicion] if posicion < len(fila) else None


def _leer_hoja(nombre: str, con_valores: Any, con_formulas: Any) -> HojaLeida:
    conocidos = ENCABEZADOS_POR_HOJA[nombre]
    columnas: dict[int, str] = {}
    filas: list[FilaLeida] = []
    for numero, (fila_valores, fila_formulas) in enumerate(
        zip(con_valores.iter_rows(), con_formulas.iter_rows(), strict=False), start=1
    ):
        if numero == 1:
            for posicion, celda in enumerate(fila_valores):
                encabezado = _texto_de_celda(celda.value)
                if encabezado in conocidos and encabezado not in columnas.values():
                    columnas[posicion] = encabezado
            continue
        valores: dict[str, str | None] = {}
        sin_cache: set[str] = set()
        for posicion, encabezado in columnas.items():
            celda_valor = _celda(fila_valores, posicion)
            celda_formula = _celda(fila_formulas, posicion)
            valor = None if celda_valor is None else _texto_de_celda(celda_valor.value)
            if (
                valor is None
                and celda_formula is not None
                and getattr(celda_formula, "data_type", None) == "f"
            ):
                sin_cache.add(encabezado)
            valores[encabezado] = valor
        if all(v is None for v in valores.values()) and not sin_cache:
            continue
        if len(filas) == LIMITE_DE_FILAS:
            raise _demasiadas_filas(nombre)
        filas.append(FilaLeida(numero, valores, frozenset(sin_cache)))
    return HojaLeida(nombre, tuple(columnas.values()), tuple(filas))


class LectorDePlantillaExcel:
    def leer(self, contenido: bytes, *, nombre: str | None = None) -> PlantillaLeida:
        if len(contenido) > LIMITE_DE_BYTES:
            raise _demasiado_grande(nombre)
        con_valores = con_formulas = None
        try:
            con_valores = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
            con_formulas = load_workbook(io.BytesIO(contenido), read_only=True, data_only=False)
            hojas = {
                hoja: _leer_hoja(hoja, con_valores[hoja], con_formulas[hoja])
                for hoja in ENCABEZADOS_POR_HOJA
                if hoja in con_valores.sheetnames
            }
        except ArchivoInvalido:
            raise
        except Exception as error:
            raise _no_es_un_excel(nombre) from error
        finally:
            for libro in (con_valores, con_formulas):
                if libro is not None:
                    libro.close()
        return PlantillaLeida(hojas=hojas)
