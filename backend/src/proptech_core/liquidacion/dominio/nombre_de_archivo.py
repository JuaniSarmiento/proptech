"""El nombre con el que baja el PDF de una expensa (H-017).

`expensa-<AAAA-MM>-<identificador>-<variante>.pdf`: sólo período, unidad y variante, nunca el
nombre de una persona, y sólo `[a-z0-9-.]` para que el valor entre sin escapes en
`Content-Disposition`.
"""

import re
import unicodedata
from datetime import date

_FUERA_DEL_ALFABETO = re.compile(r"[^a-z0-9]+", re.ASCII)


def _normalizado(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return _FUERA_DEL_ALFABETO.sub("-", sin_acentos.lower()).strip("-")


def nombre_del_pdf(periodo: date, identificador: str, variante: str) -> str:
    unidad = _normalizado(identificador) or "unidad"
    return f"expensa-{periodo:%Y-%m}-{unidad}-{_normalizado(variante)}.pdf"
