"""Errores de los pagos, sin valores del pedido ni mensajes crudos de PostgreSQL."""


class NoEncontrado(LookupError):
    def __init__(self) -> None:
        super().__init__("no encontrado")


class Conflicto(Exception):
    """El pedido es válido pero el estado no lo admite. `motivo` es un código estable que la
    pantalla traduce (por ejemplo `repetido`)."""

    def __init__(self, campo: str, motivo: str) -> None:
        self.campo = campo
        self.motivo = motivo
        super().__init__("conflicto")


class EntradaInvalida(ValueError):
    def __init__(self, campo: str, motivo: str = "valor inválido", donde: str = "body") -> None:
        self.campo = campo
        self.motivo = motivo
        #: `body` (el cuerpo o el archivo), como en el 422 de FastAPI.
        self.donde = donde
        super().__init__(f"{campo}: {motivo}")
