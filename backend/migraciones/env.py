"""Entorno de Alembic. La URL sale de Configuracion, nunca de alembic.ini."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from proptech_core.compartido.base_de_datos import Base
from proptech_core.compartido.configuracion import Configuracion

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    return Configuracion().url_sqlalchemy()


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuracion_ini = config.get_section(config.config_ini_section) or {}
    configuracion_ini["sqlalchemy.url"] = _url()
    connectable = engine_from_config(
        configuracion_ini,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
