"""Errores de aplicación sin valores del pedido ni mensajes crudos de PostgreSQL.

Mismo patrón que `complejos/aplicacion/errores.py`: `gastos` no importa
`complejos` (frontera vigilada por `test_fronteras_de_modulos.py`), así que
este módulo repite la forma en vez de compartirla.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg.errors import UniqueViolation
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class NoEncontrado(LookupError):
    def __init__(self) -> None:
        super().__init__("no encontrado")


class Conflicto(Exception):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__("conflicto")


class EntradaInvalida(ValueError):
    def __init__(
        self,
        campo: str,
        motivo: str = "valor inválido",
        tipo: str = "value_error",
        identificadores: list[str] | None = None,
    ) -> None:
        self.campo = campo
        self.motivo = motivo
        self.tipo = tipo
        self.identificadores = identificadores
        super().__init__(f"{campo}: {motivo}")


def error_de_validacion(error: ValidationError) -> EntradaInvalida:
    """Conserva la explicación de los validadores propios del dominio (L-051:
    el formato del CUIT, "mayor que cero", "primer día de un mes"), que son
    textos fijos sin el valor recibido. El resto de los errores de pydantic
    sigue como "valor inválido"."""
    errores = error.errors()
    campos = sorted({".".join(map(str, e["loc"])) for e in errores})
    explicaciones = sorted(
        {str(e["ctx"]["error"]) for e in errores if e["type"] == "value_error" and "ctx" in e}
    )
    return EntradaInvalida(", ".join(campos), "; ".join(explicaciones) or "valor inválido")


class ImportacionInvalida(Exception):
    """D6: todo o nada. `errores` junta TODAS las filas con problema (nunca
    sólo la primera), cada una como `{"fila": int, "motivo": str}`."""

    def __init__(self, errores: list[dict[str, object]]) -> None:
        self.errores = errores
        super().__init__("importación inválida")


@contextmanager
def transaccion(sesion: Session, conflictos: dict[str, str]) -> Iterator[None]:
    try:
        with sesion.begin_nested() if sesion.in_transaction() else sesion.begin():
            yield
    except IntegrityError as error:
        if isinstance(error.orig, UniqueViolation):
            campo = conflictos.get(error.orig.diag.constraint_name or "")
            if campo is not None:
                raise Conflicto(campo) from None
        raise
