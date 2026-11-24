"""El `.xlsx` de la morosidad (10a, H-028, E8): el libro sale de la misma `Morosidad` de la API.

Nunca recalcula: sólo presenta. Los montos van como números (el `Decimal` exacto pasa a `float`
sólo para la celda, con dos decimales) y con formato de moneda; los totales se suman acá con
`Dinero`, sin fórmulas. Sin email, teléfono ni documento de nadie.
"""

import re
import unicodedata
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.cuenta_corriente.aplicacion.morosidad import Morosidad

TIPO_DE_CONTENIDO = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_TITULOS = (
    "Unidad",
    "Propietarios",
    "Situación",
    "Total vencido",
    "Capital",
    "Intereses",
    "Liquidaciones vencidas",
    "Vencida desde",
    "Días",
)
_SITUACION = {
    "moroso_critico": "Moroso crítico",
    "con_deuda_vencida": "Con deuda vencida",
    "deuda_de_intereses": "Deuda de intereses",
    "bajo_umbral": "Bajo el umbral",
}
_FORMATO_DE_MONTO = '"$ "#,##0.00'
_FORMATO_DE_FECHA = "dd/mm/yyyy"


def _slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def nombre_del_archivo(edificio: str, fecha: date) -> str:
    return f"morosidad-{_slug(edificio)}-{fecha.isoformat()}.xlsx"


def _monto(hoja: Worksheet, celda: str, valor: Dinero) -> None:
    hoja[celda] = float(valor.decimal)
    hoja[celda].number_format = _FORMATO_DE_MONTO


def armar_libro(edificio: str, m: Morosidad) -> bytes:
    libro = Workbook()
    libro.remove(libro.active)  # type: ignore[arg-type]
    hoja = libro.create_sheet("Morosidad")
    negrita = Font(bold=True)
    hoja["A1"], hoja["B1"] = "Morosidad", edificio
    hoja["A2"], hoja["B2"] = "Fecha", m.fecha
    hoja["A3"], hoja["B3"] = "Intereses al", m.intereses_al
    for celda in ("B2", "B3"):
        hoja[celda].number_format = _FORMATO_DE_FECHA
    for columna, titulo in zip("ABCDEFGHI", _TITULOS, strict=True):
        hoja[f"{columna}5"] = titulo
        hoja[f"{columna}5"].font = negrita
    fila = 6
    for u in m.unidades:
        hoja[f"A{fila}"] = u.unidad
        hoja[f"B{fila}"] = ", ".join(u.propietarios) or None
        hoja[f"C{fila}"] = _SITUACION[u.etiqueta]
        _monto(hoja, f"D{fila}", u.total_vencido)
        _monto(hoja, f"E{fila}", u.capital)
        _monto(hoja, f"F{fila}", u.intereses)
        hoja[f"G{fila}"] = u.liquidaciones_vencidas
        hoja[f"H{fila}"] = u.vencida_desde
        hoja[f"H{fila}"].number_format = _FORMATO_DE_FECHA
        hoja[f"I{fila}"] = u.dias
        fila += 1
    hoja[f"A{fila}"] = "Total"
    hoja[f"A{fila}"].font = negrita
    _monto(hoja, f"D{fila}", sumar(u.total_vencido for u in m.unidades))
    _monto(hoja, f"E{fila}", sumar(u.capital for u in m.unidades))
    _monto(hoja, f"F{fila}", sumar(u.intereses for u in m.unidades))
    for columna, ancho in zip("ABCDEFGHI", (12, 36, 20, 16, 16, 16, 12, 14, 8), strict=True):
        hoja.column_dimensions[columna].width = ancho
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
