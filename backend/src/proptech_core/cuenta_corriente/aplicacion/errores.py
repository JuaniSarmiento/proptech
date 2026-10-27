"""Errores del libro, sin valores del pedido ni mensajes crudos de PostgreSQL (D10)."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import DBAPIError
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
    "TemporalmenteNoDisponible",
    "exigir_transaccion",
    "traducir",
]


class NoEncontrado(LookupError):
    def __init__(self) -> None:
        super().__init__("no encontrado")


class TemporalmenteNoDisponible(Exception):
    """La transacción completa puede reintentarse por el llamador, con la misma clave."""


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


_CONFLICTOS = {
    "uq_mov_operacion": "operacion_id",
    "uq_obligacion_operacion": "operacion_id",
    "uq_mov_corrige_a": "movimiento_id",
    "uq_emision_intento": "periodo",
    "emision_pkey": "emision_id",
    "uq_obligacion_emision": "emision_id",
    "uq_evento_emision_tipo": "emision_id",
    "uq_cuenta_unidad": "unidad_id",
    "uq_cuenta_persona": "persona_id",
}


@contextmanager
def traducir(
    sesion: Session, conflictos: dict[str, str], no_encontrados: frozenset[str] = frozenset()
) -> Iterator[None]:
    """SAVEPOINT (BE-5.1): un 23505 o 23503 traducido deja usable la transacción del llamador."""
    try:
        with sesion.begin_nested():
            yield
    except DBAPIError as error:
        restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None) or ""
        estado = getattr(error.orig, "sqlstate", None)
        campos = {**_CONFLICTOS, **conflictos}
        if estado == "23505" and restriccion in campos:
            raise Conflicto(campos[restriccion]) from None
        if estado == "23503":
            raise NoEncontrado from None
        if estado in {"40P01", "40001", "55P03", "57014"}:
            raise TemporalmenteNoDisponible from None
        raise
