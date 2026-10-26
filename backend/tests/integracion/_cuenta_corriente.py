"""Mundo ficticio y sesiones de la app para los casos de uso del libro (sección 3)."""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import psycopg
from sqlalchemy import Connection, create_engine, event, text
from sqlalchemy.orm import Session, SessionTransaction
from sqlalchemy.pool import NullPool

from proptech_core.acceso.dominio.identidad import Identidad

from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad


@dataclass(frozen=True)
class Mundo:
    admin: UUID
    admin_b: UUID
    complejo: UUID
    otro_complejo: UUID
    complejo_b: UUID
    unidades: tuple[UUID, ...]
    unidad_otro_complejo: UUID
    unidad_b: UUID
    persona: UUID
    persona_b: UUID

    @property
    def identidad(self) -> Identidad:
        return Identidad(self.admin, self.persona)

    @property
    def identidad_b(self) -> Identidad:
        return Identidad(self.admin_b, self.persona_b)


def sembrar(base: BaseDeEdificio, unidades: int = 12) -> Mundo:
    """Datos confirmados: las pruebas de concurrencia los leen desde dos conexiones."""
    admin, admin_b = uuid4(), uuid4()
    complejo, otro, complejo_b = uuid4(), uuid4(), uuid4()
    persona, persona_b = uuid4(), uuid4()
    with base.conectar_app() as c:
        c.autocommit = False
        ids: list[UUID] = []
        for adm, complejos, per in (
            (admin, (complejo, otro), persona),
            (admin_b, (complejo_b,), persona_b),
        ):
            fijar_tenant(c, adm)
            c.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Ficticia')", (adm,))
            c.execute(
                "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Ficticia')",
                (per, adm),
            )
            for cx in complejos:
                c.execute(
                    "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                    "VALUES (%s, %s, 'Edificio ficticio', 'Mendoza')",
                    (cx, adm),
                )
        fijar_tenant(c, admin)
        for n in range(unidades):
            ids.append(insertar_unidad(c, admin, complejo, f"U{n:03d}", coeficiente="0.010000"))
        unidad_otro = insertar_unidad(c, admin, otro, "X1")
        fijar_tenant(c, admin_b)
        unidad_b = insertar_unidad(c, admin_b, complejo_b, "B1")
        c.commit()
    return Mundo(
        admin,
        admin_b,
        complejo,
        otro,
        complejo_b,
        tuple(ids),
        unidad_otro,
        unidad_b,
        persona,
        persona_b,
    )


@contextmanager
def sesion_app(
    base: BaseDeEdificio, admin: UUID, *, aislamiento: str | None = None, comenzar: bool = True
) -> Iterator[Session]:
    """Session de la app con el tenant fijado al empezar CADA transacción (set_config local)."""

    def conectar() -> psycopg.Connection:
        conexion = base.conectar_app()
        conexion.autocommit = False
        return conexion

    opciones: dict[str, Any] = {}
    if aislamiento is not None:
        opciones["isolation_level"] = aislamiento
    engine = create_engine(
        "postgresql+psycopg://", creator=conectar, poolclass=NullPool, **opciones
    )

    with Session(engine) as sesion:

        @event.listens_for(sesion, "after_begin")
        def _tenant(s: Session, t: SessionTransaction, conexion: Connection) -> None:
            conexion.execute(
                text("SELECT set_config('app.administracion_id', :a, true)"), {"a": str(admin)}
            )
            # L-011: el corte del lado de PostgreSQL, no sólo el timeout del cliente.
            conexion.execute(text("SET LOCAL lock_timeout = '20s'"))

        try:
            if comenzar:
                sesion.begin()
            yield sesion
        finally:
            sesion.rollback()
    engine.dispose()


def contar_escrituras(sesion: Session) -> list[str]:
    """Registra cada INSERT que la sesión manda a PostgreSQL (RC-09: cero escrituras)."""
    vistas: list[str] = []

    @event.listens_for(sesion.get_bind(), "before_cursor_execute")
    def _ver(conn: Any, cursor: Any, sentencia: str, *args: Any) -> None:
        if sentencia.lstrip().upper().startswith("INSERT"):
            vistas.append(sentencia)

    return vistas


def en_hilo(funcion: Callable[[], Any]) -> tuple[threading.Thread, dict[str, Any]]:
    resultado: dict[str, Any] = {}

    def correr() -> None:
        try:
            resultado["valor"] = funcion()
        except BaseException as error:
            resultado["error"] = error

    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()
    return hilo, resultado
