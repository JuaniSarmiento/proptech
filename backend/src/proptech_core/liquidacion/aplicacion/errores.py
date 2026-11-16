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
    def __init__(self, campo: str, motivo: str = "valor inválido", donde: str = "path") -> None:
        self.campo = campo
        self.motivo = motivo
        #: `path` (el período de la ruta) o `body` (el cuerpo), como en el 422 de FastAPI.
        self.donde = donde
        super().__init__(f"{campo}: {motivo}")


class SinPermiso(Exception):
    """Falta una acción que sólo se sabe después de mirar el pedido (por ejemplo, aceptar un
    bloqueante al emitir). `accion` es el valor del permiso faltante."""

    def __init__(self, accion: str) -> None:
        self.accion = accion
        super().__init__("sin_permiso")


class ControlDuro(Exception):
    """El período tiene controles duros activos: no se emite aunque se pida aceptarlos."""

    def __init__(self, codigos: tuple[str, ...]) -> None:
        self.codigos = codigos
        super().__init__("control_duro")
