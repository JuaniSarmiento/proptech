"""Errores de aplicación sin valores del pedido ni mensajes crudos de PostgreSQL."""

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
    """`tipo="value_error"` por default: vocabulario cerrado de Pydantic, el
    `motivo` nunca llega al cliente (L-007, `cliente.ts` lo descarta siempre).
    `identificadores`, en cambio, es una lista cerrada de datos propios del
    edificio (nunca texto libre ni el valor del pedido) que sí viaja al
    cliente estructurada — ver `fuera_de_rango` en `editar_edificio`."""

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
    campos = sorted({".".join(map(str, e["loc"])) for e in error.errors()})
    return EntradaInvalida(", ".join(campos))


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
