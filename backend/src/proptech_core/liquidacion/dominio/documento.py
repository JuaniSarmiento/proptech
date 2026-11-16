"""El contenido del PDF de la expensa (7, H-015, R19, D-160): puro, sin base ni WeasyPrint.

Se arma siempre desde lo **guardado** al emitir (la lectura de `leer_liquidacion`), nunca
recalculado:
el PDF archivado tiene que decir lo mismo que la liquidación (CCyC art. 2067 inc. i). Los montos
llegan como texto y se formatean con punto de miles y coma decimal sin pasar por `float`. El modelo
de contenido es el de la Ley 941 de CABA (D-160), sin presentarlo como exigencia legal en Mendoza.

La variante `sin_extraordinaria` (D-106, la del inquilino) es la misma expensa sin el bloque
extraordinario: ni sus categorías ni su importe, y su total es el de la unidad menos la
extraordinaria.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from html import escape
from typing import Any

COMPLETA = "completa"
SIN_EXTRAORDINARIA = "sin_extraordinaria"
VARIANTES = (COMPLETA, SIN_EXTRAORDINARIA)

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_MONTO = re.compile(r"(-?)([0-9]+)\.([0-9]{2})", re.ASCII)


def _inicial(palabra: str) -> str:
    """La primera letra o dígito de la palabra, sin tilde y en mayúscula (`Álamos` -> `A`)."""
    for caracter in unicodedata.normalize("NFD", palabra):
        if unicodedata.category(caracter).startswith("M"):
            continue
        if caracter.isalnum():
            return caracter.upper()
    return ""


def codigo_de_transferencia(nombre_del_edificio: str, identificador: str) -> str:
    """R19: las iniciales en mayúscula de las palabras del nombre del edificio, un guion y el
    identificador de la unidad (`Torre Ficticia`, `1B` -> `TF-1B`)."""
    iniciales = "".join(_inicial(palabra) for palabra in nombre_del_edificio.split())
    return f"{iniciales}-{identificador}"


def monto_para_el_pdf(texto: str) -> str:
    """`48350.00` -> `48.350,00`. Sólo acepta el texto de un monto con dos decimales (nunca un
    `float`): un monto mal formado frena el PDF en vez de salir con un número inventado."""
    coincidencia = _MONTO.fullmatch(texto) if isinstance(texto, str) else None
    if coincidencia is None:
        raise ValueError("monto: se esperaba un texto con dos decimales")
    signo, enteros, decimales = coincidencia.groups()
    con_miles = f"{int(enteros):,}".replace(",", ".")
    return f"{signo}{con_miles},{decimales}"


def periodo_en_palabras(periodo: date) -> str:
    return f"{_MESES[periodo.month - 1]} de {periodo.year}"


def fecha_corta(dia: date) -> str:
    return f"{dia.day:02d}/{dia.month:02d}/{dia.year}"


def _fila(texto: str, importe: str) -> str:
    return f'<tr><td>{escape(texto)}</td><td class="monto">{monto_para_el_pdf(importe)}</td></tr>'


def _bloque(
    titulo: str, bloque: dict[str, Any], grupos: dict[str, str], por_grupo: list[dict[str, Any]],
    clave: str, propia: str,
) -> str:  # fmt: skip
    filas = "".join(_fila(c["nombre"], c["importe"]) for c in bloque["categorias"])
    partes = "".join(
        _fila(f"Su parte en {grupos.get(g['grupo_id'], 'el grupo')}", g[clave])
        for g in por_grupo
        if Decimal(g[clave]) != 0
    )
    return (
        f"<section><h2>{escape(titulo)}</h2>"
        '<table><thead><tr><th>Categoría</th><th class="monto">Total del edificio</th></tr></thead>'
        f"<tbody>{filas}</tbody></table>"
        f"<table><tbody>{partes}{_fila(f'{titulo} de la unidad', propia)}</tbody></table></section>"
    )


_ESTILO = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "DejaVu Sans", sans-serif; font-size: 10pt; color: #1b1b1b; }
h1 { font-size: 16pt; margin: 0 0 2mm; }
h2 { font-size: 11pt; margin: 6mm 0 2mm; border-bottom: 0.3mm solid #888; padding-bottom: 1mm; }
p { margin: 1mm 0; }
table { width: 100%; border-collapse: collapse; margin-bottom: 2mm; }
th, td { text-align: left; padding: 1mm 0; }
.monto { text-align: right; white-space: nowrap; }
.total td { font-weight: bold; border-top: 0.4mm solid #1b1b1b; padding-top: 2mm; }
.codigo { font-size: 12pt; font-weight: bold; }
"""


def html_de_la_expensa(
    liquidacion: dict[str, Any], *, unidad_id: str, nombre_del_edificio: str, variante: str
) -> str:
    """El HTML de la expensa de una unidad, desde la liquidación guardada."""
    if variante not in VARIANTES:
        raise ValueError("variante: desconocida")
    unidad = next((u for u in liquidacion["unidades"] if u["unidad_id"] == unidad_id), None)
    if unidad is None:
        raise ValueError("unidad: no está en la liquidación")
    con_extraordinaria = variante == COMPLETA
    grupos = {g["grupo_id"]: g["nombre"] for g in liquidacion["grupos"]}
    total = Decimal(unidad["total"])
    if not con_extraordinaria:
        total -= Decimal(unidad["extraordinaria"])
    periodo = date.fromisoformat(liquidacion["periodo"])
    vencimiento = date.fromisoformat(liquidacion["vencimiento"])
    codigo = codigo_de_transferencia(nombre_del_edificio, unidad["identificador"])
    cargos = "".join(_fila(c["concepto"], c["importe"]) for c in unidad["cargos_particulares"])
    bloques = _bloque(
        "Ordinaria",
        liquidacion["bloques"]["ordinario"],
        grupos,
        unidad["por_grupo"],
        "ordinaria",
        unidad["ordinaria"],
    )
    if con_extraordinaria:
        bloques += _bloque(
            "Extraordinaria",
            liquidacion["bloques"]["extraordinario"],
            grupos,
            unidad["por_grupo"],
            "extraordinaria",
            unidad["extraordinaria"],
        )
    detalle = (
        f"{_fila('Fondo de reserva', unidad['fondo_de_reserva'])}"
        f"{cargos}{_fila('Intereses', unidad['intereses'])}"
    )
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f"<title>Expensa {escape(periodo_en_palabras(periodo))} · {escape(unidad['identificador'])}"
        f"</title><style>{_ESTILO}</style></head><body>"
        f"<h1>{escape(nombre_del_edificio)}</h1>"
        f"<p>Expensa de {escape(periodo_en_palabras(periodo))}</p>"
        f"<p>Unidad: <strong>{escape(unidad['identificador'])}</strong></p>"
        f"<p>Vencimiento: {fecha_corta(vencimiento)}</p>"
        f'<p>Código para la transferencia: <span class="codigo">{escape(codigo)}</span></p>'
        f"{bloques}"
        "<section><h2>Fondo, cargos e intereses</h2>"
        f"<table><tbody>{detalle}</tbody></table></section>"
        "<section><h2>Estado de cuenta</h2><table><tbody>"
        f"{_fila('Saldo anterior', unidad['saldo_anterior'])}"
        f'<tr class="total"><td>Total de la expensa</td>'
        f'<td class="monto">{monto_para_el_pdf(f"{total:.2f}")}</td></tr>'
        "</tbody></table></section></body></html>"
    )
