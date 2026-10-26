"""Errores del libro, sin valores del pedido ni mensajes crudos de PostgreSQL (D10)."""

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg.errors import ForeignKeyViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from proptech_core.acceso.aplicacion.auditoria import RegistroFueraDeTransaccion
from proptech_core.cuenta_corriente.dominio.errores import EntradaInvalida

__all__ = [
    "AislamientoNoAdmitido",
    "BloqueoFueraDeOrden",
    "CandadoIncompleto",
    "Conflicto",
    "EntradaInvalida",
    "IdentidadDeOtraAdministracion",
    "NoEncontrado",
    "RegistroFueraDeTransaccion",
    "exigir_transaccion",
    "traducir",
]


class NoEncontrado(LookupError):
    def __init__(self) -> None:
        super().__init__("no encontrado")


class Conflicto(Exception):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__("conflicto")


class AislamientoNoAdmitido(Exception):
    """D2, DB-4: el candado sólo protege en READ COMMITTED."""


class CandadoIncompleto(Exception):
    """D2, QA-6: el SELECT ... FOR UPDATE no devolvió una fila por cuenta."""


class BloqueoFueraDeOrden(Exception):
    """RC2-01: una transacción no puede sumar una cuenta menor que la mayor ya bloqueada."""


class IdentidadDeOtraAdministracion(Exception):
    """D3, BE-5.2: la identidad no coincide con el tenant de la sesión."""


def exigir_transaccion(sesion: Session) -> None:
    if not sesion.in_transaction():
        raise RegistroFueraDeTransaccion("el libro exige una sesión ya en transacción (D3)")


@contextmanager
def traducir(
    sesion: Session, conflictos: dict[str, str], no_encontrados: frozenset[str] = frozenset()
) -> Iterator[None]:
    """SAVEPOINT (BE-5.1): un 23505 o 23503 traducido deja usable la transacción del llamador."""
    try:
        with sesion.begin_nested():
            yield
    except IntegrityError as error:
        restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None) or ""
        if isinstance(error.orig, UniqueViolation) and restriccion in conflictos:
            raise Conflicto(conflictos[restriccion]) from None
        if isinstance(error.orig, ForeignKeyViolation) and restriccion in no_encontrados:
            raise NoEncontrado from None
        raise
