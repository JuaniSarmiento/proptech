"""Engine de SQLAlchemy y Base declarativa, usados también por Alembic."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, SessionTransaction, sessionmaker

from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.seguimiento import request_id_actual


class Base(DeclarativeBase):
    """Base declarativa común para todos los modelos del dominio."""


def crear_engine(
    configuracion: Configuracion, connect_args: dict[str, object] | None = None
) -> Engine:
    """Crea el engine sincrónico a partir de la configuración.

    `connect_args` se pasa a `create_engine`, nunca a `execution_options`: ahí
    SQLAlchemy lo ignora en silencio y el timeout de conexión no se aplica.

    Los parámetros del pool (`pool_pre_ping`, `pool_size`, `pool_recycle`,
    `pool_timeout`) y el timeout de conexión salen de la configuración (D18,
    M14), para que el engine de la API y el del worker sean gemelos (L-009).
    Un `connect_args` explícito pisa el `connect_timeout` de la
    configuración para ese valor puntual; el resto de `connect_args` llega
    intacto.
    """
    connect_args_finales: dict[str, object] = {
        "connect_timeout": configuracion.db_connect_timeout_s,
        **(connect_args or {}),
    }
    return create_engine(
        configuracion.url_sqlalchemy(),
        connect_args=connect_args_finales,
        pool_pre_ping=configuracion.db_pool_pre_ping,
        pool_size=configuracion.db_pool_size,
        pool_recycle=configuracion.db_pool_recycle_s,
        pool_timeout=configuracion.db_pool_timeout_s,
    )


def crear_fabrica_de_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Crea la fábrica de sesiones ligada al engine dado."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def registrar_application_name(fabrica: sessionmaker[Session], prefijo: str) -> None:
    """Registra en `fabrica` un evento `after_begin` (D8) que, al abrir cada
    transacción, fija `application_name` a `"<prefijo>:<request_id>"` si hay
    un `request_id` en curso (la `ContextVar` de `seguimiento.py`).

    `set_config(..., true)` es **local a la transacción**: al confirmar o
    revertir, la conexión vuelve al nombre base que se le dio en
    `connect_args` (por eso el pedido siguiente del mismo pool no lo
    hereda). El parámetro va ligado, nunca interpolado en el SQL.
    """

    @event.listens_for(fabrica, "after_begin")
    def _after_begin(
        session: Session, transaction: SessionTransaction, connection: Connection
    ) -> None:
        request_id = request_id_actual.get()
        if request_id is None:
            return
        connection.execute(
            text("SELECT set_config('application_name', :nombre, true)"),
            {"nombre": f"{prefijo}:{request_id}"},
        )


def obtener_sesion(fabrica: sessionmaker[Session]) -> Iterator[Session]:
    """Dependencia de FastAPI: abre y cierra una sesión por request."""
    sesion = fabrica()
    try:
        yield sesion
    finally:
        sesion.close()
