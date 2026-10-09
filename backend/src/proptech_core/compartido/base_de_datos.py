"""Engine de SQLAlchemy y Base declarativa, usados también por Alembic."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from proptech_core.compartido.configuracion import Configuracion


class Base(DeclarativeBase):
    """Base declarativa común para todos los modelos del dominio."""


def crear_engine(
    configuracion: Configuracion, connect_args: dict[str, object] | None = None
) -> Engine:
    """Crea el engine sincrónico a partir de la configuración.

    `connect_args` se pasa a `create_engine`, nunca a `execution_options`: ahí
    SQLAlchemy lo ignora en silencio y el timeout de conexión no se aplica.
    """
    return create_engine(configuracion.url_sqlalchemy(), connect_args=connect_args or {})


def crear_fabrica_de_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Crea la fábrica de sesiones ligada al engine dado."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def obtener_sesion(fabrica: sessionmaker[Session]) -> Iterator[Session]:
    """Dependencia de FastAPI: abre y cierra una sesión por request."""
    sesion = fabrica()
    try:
        yield sesion
    finally:
        sesion.close()
