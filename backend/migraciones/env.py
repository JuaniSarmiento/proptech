"""Entorno de Alembic. La URL sale de ConfiguracionBaseDeDatos, nunca de alembic.ini.

Alembic sólo necesita las variables de PostgreSQL: usa `ConfiguracionBaseDeDatos`,
no `Configuracion`, para no acoplar el trabajo de migraciones a Redis ni al
archivo de parámetros del sistema (D11, tarea 6.1)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from proptech_core.compartido.base_de_datos import Base
from proptech_core.compartido.configuracion import ConfiguracionBaseDeDatos

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    # Sólo las variables de PostgreSQL (D11, tarea 6.1): Alembic no necesita
    # Redis ni el archivo de parámetros del sistema.
    return ConfiguracionBaseDeDatos().url_sqlalchemy()


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
