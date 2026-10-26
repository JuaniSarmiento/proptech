"""Errores del dominio del libro, sin valores del pedido (D10)."""


class EntradaInvalida(ValueError):
    def __init__(self, campo: str, motivo: str = "valor inválido") -> None:
        self.campo = campo
        self.motivo = motivo
        super().__init__(f"{campo}: {motivo}")
