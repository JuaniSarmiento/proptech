"""Clave derivada del nombre, para grupos y categorías (D7, tarea 4.1):
siempre ASCII, empieza con letra, `[a-z0-9_]`, sin guiones bajos repetidos
ni al final, hasta 40 caracteres, desempatada con un sufijo numérico contra
las claves que el edificio ya tiene. `None` cuando el nombre no tiene
ningún carácter alfabético utilizable (p. ej. "123" o "— —")."""

import re
import unicodedata
from collections.abc import Collection

_MAXIMO = 40
_SOLO_DIGITOS_O_GUION = re.compile(r"^[0-9_]*$")


def _normalizado(nombre: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)
    )
    base = re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower())
    return base.strip("_")


def derivar_clave(nombre: str, existentes: Collection[str]) -> str | None:
    base = _normalizado(nombre)
    if base == "" or _SOLO_DIGITOS_O_GUION.fullmatch(base) is not None:
        return None
    if base[0].isdigit():
        base = "g_" + base
    base = base[:_MAXIMO].rstrip("_")
    if base == "":
        return None
    ocupadas = set(existentes)
    if base not in ocupadas:
        return base
    sufijo = 2
    while True:
        marca = f"_{sufijo}"
        candidato = base[: _MAXIMO - len(marca)].rstrip("_") + marca
        if candidato not in ocupadas:
            return candidato
        sufijo += 1
