"""Entorno de Alembic. La URL sale de ConfiguracionDelMigrador, nunca de alembic.ini.

Alembic corre como `proptech_migrador` (D1, D2 del cambio 2a): usa
`ConfiguracionDelMigrador`, no `Configuracion` (el rol de la app) ni
`ConfiguracionDeArranque` (el rol de arranque, que sólo usa el paso de roles),
para no acoplar el trabajo de migraciones a Redis ni al archivo de parámetros
del sistema (D11, tarea 6.1; D3, tarea 2.1)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL

from proptech_core.compartido.base_de_datos import Base
from proptech_core.compartido.configuracion import ConfiguracionDelMigrador

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False (D7, M16): el default (True) deshabilita
    # en silencio todo logger creado antes de correr las migraciones (los
    # tests de integración que ya llamaron a configurar_logs, o la API si
    # algún día migra al arrancar), incluidos los de proptech_core.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> URL:
    # Sólo las variables de PostgreSQL del migrador (D11, tarea 6.1; D3, tarea
    # 2.1): Alembic no necesita Redis ni el archivo de parámetros del sistema.
    return ConfiguracionDelMigrador().url_sqlalchemy()


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
