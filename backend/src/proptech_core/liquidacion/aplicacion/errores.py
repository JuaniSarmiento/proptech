"""Errores de la liquidación, sin valores del pedido ni mensajes crudos de PostgreSQL."""


class NoEncontrado(LookupError):
    def __init__(self) -> None:
        super().__init__("no encontrado")


class Conflicto(Exception):
    """El pedido es válido pero el estado del edificio no lo admite. `motivo` es un código estable
    que la pantalla traduce (por ejemplo `periodo_anterior_sin_emitir`)."""

    def __init__(self, campo: str, motivo: str) -> None:
        self.campo = campo
        self.motivo = motivo
        super().__init__("conflicto")


class EntradaInvalida(ValueError):
    def __init__(self, campo: str, motivo: str = "valor inválido") -> None:
        self.campo = campo
        self.motivo = motivo
        super().__init__(f"{campo}: {motivo}")
