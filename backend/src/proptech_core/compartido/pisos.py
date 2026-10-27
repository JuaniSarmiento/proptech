"""Vocabulario de pisos de un edificio (D3, tarea 3.1): `PB` siempre,
`SS1..SS<subsuelos>`, `1..<pisos>`. Límites del `CHECK` de la migración
`0024`: 0 a 60 pisos, 0 a 5 subsuelos — los mismos que `PATRON_PISO` fija
en el propio patrón (coincidencia completa, sólo ASCII, L-008)."""

import re

#: Misma forma que el `CHECK ck_unidad_piso` de la migración `0024`
#: (D3): el rango 1 a 60 queda escrito en el patrón, no sólo en el texto
#: de la decisión. `fullmatch`, nunca `match` (L-002): sin `re.MULTILINE`,
#: `$` matchea antes de un `\n` final, así que `match()` aceptaría "1\n".
PATRON_PISO = re.compile(r"^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$", re.ASCII)

_PISOS_MAXIMO = 60
_SUBSUELOS_MAXIMO = 5


def vocabulario_de_pisos(*, pisos: int, subsuelos: int) -> frozenset[str]:
    """El vocabulario exacto de un edificio con `pisos` sobre planta baja y
    `subsuelos` subsuelos: `PB` siempre, `SS1..SS<subsuelos>`,
    `1..<pisos>`."""
    if not (0 <= pisos <= _PISOS_MAXIMO):
        raise ValueError(f"pisos fuera de rango (0 a {_PISOS_MAXIMO})")
    if not (0 <= subsuelos <= _SUBSUELOS_MAXIMO):
        raise ValueError(f"subsuelos fuera de rango (0 a {_SUBSUELOS_MAXIMO})")
    vocabulario = {"PB"}
    vocabulario.update(f"SS{n}" for n in range(1, subsuelos + 1))
    vocabulario.update(str(n) for n in range(1, pisos + 1))
    return frozenset(vocabulario)


def piso_valido(piso: str, *, pisos: int, subsuelos: int) -> bool:
    """`True` si `piso` está en el vocabulario de un edificio con `pisos` y
    `subsuelos` (D3, tarea 3.3): usa `vocabulario_de_pisos`, no
    `PATRON_PISO` solo — `PATRON_PISO` sólo valida la FORMA (lo que la base
    puede expresar con un `CHECK`), nunca que el piso esté dentro del
    rango de ESTE edificio en particular."""
    return piso in vocabulario_de_pisos(pisos=pisos, subsuelos=subsuelos)
