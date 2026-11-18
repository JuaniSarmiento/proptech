"""El banco y el número de operación, comparables (E3, D-163).

Dos pagos son "el mismo" si banco y número coinciden después de quitar espacios (cualquier
separador Unicode), guiones y puntos, pasar a minúscula y sacar las tildes. Así `Banco Nación` y
` banco  nacion ` son el mismo banco, y `12-345.678` y `12 345 678`, el mismo número.
"""

from __future__ import annotations

import unicodedata

_SEPARADORES = frozenset("-.")


def normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return "".join(c for c in sin_tildes.lower() if not c.isspace() and c not in _SEPARADORES)
