"""D-104: nombres recortados y email normalizado, errores sin valores."""

import re

from proptech_core.compartido.texto import recortado_sin_control


def nombre_valido(valor: str, campo: str = "nombre") -> str:
    try:
        return recortado_sin_control(valor)
    except ValueError:
        raise ValueError(campo + ": valor inválido") from None


def email_valido(valor: str) -> str:
    valor = nombre_valido(valor, "email").lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", valor):
        raise ValueError("email: valor inválido")
    return valor
