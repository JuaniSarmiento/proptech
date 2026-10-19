"""Texto libre que entra del cliente: nunca el valor en el error (L-007,
R3A-1 y R3A-6 del cambio 3a, vuelta 1 de correcciones).

Regla R3B-1/7: se rechazan las categorías generales Unicode Cc, Cf, Cs,
Co y Cn (controles, formato, surrogates, uso privado y no asignados), y
Zl/Zp (separadores de línea/párrafo). También los Default_Ignorable de
categoría Mn/Lo: no todos los invisibles son Cf. Se conservan las letras,
marcas visibles (incluido acento combinante), números, signos y espacios Zs.
No se hacen NFC, casefold ni cambios de espacios internos.

Dos funciones para dos frentes de la misma familia:

- `sin_caracteres_de_control`: cualquier carácter de control Unicode
  (y los caracteres Unicode inseguros de la regla anterior) revienta el driver de PostgreSQL con
  un error que nadie traduce (`sqlalchemy.exc.DataError`); se rechaza acá,
  antes de llegar a la base, con un 422 genérico que nunca repite el
  carácter.
- `recortado_sin_control`: lo mismo, más recorte de espacios al borde.
  Decisión del cambio 3a: normalizar, no rechazar (R3A-6) — "1A " y "1A" son
  la misma unidad, " limpieza" y "Limpieza" la misma categoría. Si después
  de recortar no queda nada, es el mismo error que un campo vacío.

Se usan con `AfterValidator` sobre el `str` ya validado por pydantic
(longitud incluida): `max_length` se mide sobre el texto crudo, no sobre el
recortado, a propósito.
"""

from __future__ import annotations

import unicodedata

# Complemento Mn/Lo de Default_Ignorable_Code_Point (Unicode 17):
# https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt
# El resto de la propiedad ya queda rechazado por su categoría C*.
_IGNORABLES_NO_C = (
    (0x034F, 0x034F),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180D),
    (0x180F, 0x180F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFFA0, 0xFFA0),
    (0xE0100, 0xE01EF),
)


def _tiene_caracter_de_control(valor: str) -> bool:
    return any(
        unicodedata.category(c).startswith("C")
        or unicodedata.category(c) in {"Zl", "Zp"}
        or any(inicio <= ord(c) <= fin for inicio, fin in _IGNORABLES_NO_C)
        for c in valor
    )


def sin_caracteres_de_control(valor: str) -> str:
    if _tiene_caracter_de_control(valor):
        raise ValueError("no puede contener caracteres de control, invisibles o no representables")
    return valor


def recortado_sin_control(valor: str) -> str:
    recortado = sin_caracteres_de_control(valor).strip()
    if not recortado:
        raise ValueError("no puede quedar vacío después de recortar espacios")
    return recortado
