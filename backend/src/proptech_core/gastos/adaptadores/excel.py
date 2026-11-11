"""Adaptador real de `LectorDePlanillaDeCargos` (D6): `openpyxl` con `read_only=True` y
`data_only=True`, sin seguir enlaces externos. Las fórmulas NO se leen como texto crudo ni se
evalúan: `data_only=True` entrega el valor en caché que Excel guardó con el archivo, y una fórmula
sin valor guardado (un archivo armado por un script) llega como celda vacía, es decir `None`
(probado en `tests/unitarios/test_lector_de_planilla_excel.py`, L-066). Columnas fijas por
posición: A=unidad, B=concepto, C=importe; la fila 1 es encabezado y se descarta.
"""

from __future__ import annotations

import io

from openpyxl import load_workbook

from proptech_core.gastos.puertos import FilaCargoImportada


class PlanillaInvalida(Exception):
    """El archivo no es una planilla legible (no es xlsx, está corrupta)."""


class LectorDePlanillaExcel:
    def leer(self, contenido: bytes) -> list[FilaCargoImportada]:
        try:
            libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        except Exception as error:
            raise PlanillaInvalida("no se pudo leer la planilla") from error
        try:
            hoja = libro.active
            if hoja is None:
                return []
            filas: list[FilaCargoImportada] = []
            for numero, fila in enumerate(hoja.iter_rows(min_row=2, max_col=3), start=2):
                valores = [c.value for c in fila]
                while len(valores) < 3:
                    valores.append(None)
                unidad, concepto, importe = valores[:3]
                filas.append(
                    FilaCargoImportada(
                        numero_de_fila=numero,
                        unidad_identificador=None if unidad is None else str(unidad).strip(),
                        concepto=None if concepto is None else str(concepto).strip(),
                        importe=None if importe is None else str(importe).strip(),
                    )
                )
            return filas
        finally:
            libro.close()
