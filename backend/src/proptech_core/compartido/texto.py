"""Texto libre que entra del cliente: nunca el valor en el error (L-007,
R3A-1 y R3A-6 del cambio 3a, vuelta 1 de correcciones).

Dos funciones para dos frentes de la misma familia:

- `sin_caracteres_de_control`: cualquier carácter de control Unicode
  (categoría `Cc`, que incluye U+0000) revienta el driver de PostgreSQL con
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


def _tiene_caracter_de_control(valor: str) -> bool:
    return any(unicodedata.category(c) == "Cc" for c in valor)


def sin_caracteres_de_control(valor: str) -> str:
    if _tiene_caracter_de_control(valor):
        raise ValueError("no puede contener caracteres de control")
    return valor


def recortado_sin_control(valor: str) -> str:
    recortado = sin_caracteres_de_control(valor).strip()
    if not recortado:
        raise ValueError("no puede quedar vacío después de recortar espacios")
    return recortado
