"""El contenido del certificado de libre deuda y su huella (H-041, R21, D-171), sin base.

El certificado es una foto de lo que el libro sabía a la fecha de corte. Los montos viajan como
texto con dos decimales (nunca `float`). La huella es el SHA-256 de ese contenido, canónico y
determinístico: no depende del identificador del certificado ni del instante de la emisión, así que
dos emisiones con el mismo corte y el libro sin cambios dan la misma.
"""

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import date
from html import escape
from typing import Any

_MONTO = re.compile(r"(-?)([0-9]+)\.([0-9]{2})", re.ASCII)


def monto_para_el_pdf(texto: str) -> str:
    """`20720.00` -> `20.720,00`. Sólo acepta el texto de un monto con dos decimales."""
    coincidencia = _MONTO.fullmatch(texto) if isinstance(texto, str) else None
    if coincidencia is None:
        raise ValueError("monto: se esperaba un texto con dos decimales")
    signo, enteros, decimales = coincidencia.groups()
    return f"{signo}{int(enteros):,}".replace(",", ".") + f",{decimales}"


def fecha_corta(dia: date) -> str:
    return f"{dia.day:02d}/{dia.month:02d}/{dia.year}"


def contenido_del_certificado(
    *,
    unidad_id: str,
    fecha_de_corte: date,
    capital: str,
    intereses: str,
    interes_corrido: str,
    en_revision: Sequence[dict[str, str]],
    vencen_despues: Sequence[dict[str, str]],
) -> dict[str, Any]:
    """Lo que entra en la huella. El saldo es siempre `capital + intereses`."""
    centavos = int(capital.replace(".", "")) + int(intereses.replace(".", ""))
    saldo = f"{centavos // 100}.{centavos % 100:02d}"
    return {
        "unidad_id": unidad_id,
        "fecha_de_corte": fecha_de_corte.isoformat(),
        "saldo": saldo,
        "capital": capital,
        "intereses": intereses,
        "interes_corrido": interes_corrido,
        "en_revision": [dict(p) for p in en_revision],
        "vencen_despues": [dict(c) for c in vencen_despues],
    }


def huella_del_certificado(contenido: dict[str, Any]) -> str:
    canonico = json.dumps(contenido, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonico.encode("ascii")).hexdigest()


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
.id { font-family: "DejaVu Sans Mono", monospace; font-size: 8pt; white-space: nowrap; }
.leyenda { font-size: 14pt; font-weight: bold; margin: 5mm 0; }
.nota { font-size: 8pt; color: #444; margin-top: 6mm; }
"""


_ROTULO_DEL_CORRIDO = "Interés corrido hasta el corte (no registrado, no suma al saldo)"
_NOTA = "Refleja lo registrado en el libro de la cuenta corriente a la fecha de corte."


def _fila(texto: str, importe: str, *, clase: str = "") -> str:
    atributo = f' class="{clase}"' if clase else ""
    return (
        f"<tr{atributo}><td>{escape(texto)}</td>"
        f'<td class="monto">{monto_para_el_pdf(importe)}</td></tr>'
    )


def html_del_certificado(
    contenido: dict[str, Any],
    *,
    certificado_id: str,
    nombre_del_edificio: str,
    identificador_de_la_unidad: str,
) -> str:
    """El HTML del PDF, desde el contenido guardado y ya escapado. La leyenda "libre de deuda" sale
    sólo si el saldo es cero."""
    corte = date.fromisoformat(contenido["fecha_de_corte"])
    huella = huella_del_certificado(contenido)
    libre = contenido["saldo"] == "0.00"
    leyenda = '<p class="leyenda">Libre de deuda</p>' if libre else ""
    en_revision = "".join(
        f"<tr><td>{escape(p['banco'])} · operación {escape(p['numero_de_operacion'])}, "
        f"transferido el {fecha_corta(date.fromisoformat(p['fecha_de_transferencia']))}</td>"
        f'<td class="monto">{monto_para_el_pdf(p["importe"])}</td></tr>'
        for p in contenido["en_revision"]
    )
    vencen = "".join(
        _fila(
            f"Período {fecha_corta(date.fromisoformat(c['periodo']))[3:]}, "
            f"vence el {fecha_corta(date.fromisoformat(c['vencimiento']))}",
            c["importe"],
        )
        for c in contenido["vencen_despues"]
    )
    bloque_en_revision = (
        "<section><h2>Pagos informados en revisión (no restan del saldo)</h2>"
        f"<table><tbody>{en_revision}</tbody></table></section>"
        if en_revision
        else ""
    )
    bloque_vencen = (
        "<section><h2>Cuotas que vencen después del corte (no suman al saldo)</h2>"
        f"<table><tbody>{vencen}</tbody></table></section>"
        if vencen
        else ""
    )
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        f"<title>Certificado de libre deuda</title><style>{_ESTILO}</style></head><body>"
        "<h1>Certificado de libre deuda</h1>"
        f'<p class="id">Certificado {escape(certificado_id)}</p>'
        f"<p>Edificio: {escape(nombre_del_edificio)}</p>"
        f"<p>Unidad: {escape(identificador_de_la_unidad)}</p>"
        f"<p>Fecha de corte: {fecha_corta(corte)}</p>"
        f"{leyenda}"
        "<section><h2>Deuda a la fecha de corte</h2><table><tbody>"
        f"{_fila('Capital', contenido['capital'])}"
        f"{_fila('Intereses registrados', contenido['intereses'])}"
        f"{_fila('Saldo', contenido['saldo'], clase='total')}"
        "</tbody></table>"
        "<table><tbody>"
        f"{_fila(_ROTULO_DEL_CORRIDO, contenido['interes_corrido'])}"
        "</tbody></table></section>"
        f"{bloque_en_revision}{bloque_vencen}"
        f'<p class="nota">Huella del certificado: <span class="id">{escape(huella)}</span></p>'
        f'<p class="nota">{_NOTA}</p>'
        "</body></html>"
    )
