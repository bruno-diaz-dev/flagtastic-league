"""Alembic runtime configuration for the project's psycopg connection URL."""

import os

from sqlalchemy.engine import make_url

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Alembic owns schema changes and requires an explicit target database.
config = context.config

database_url = os.getenv("DATABASE_URL")

if database_url is None:
    raise RuntimeError("DATABASE_URL is not configured")

sqlalchemy_url = make_url(database_url).set(
    drivername="postgresql+psycopg"
)

config.set_main_option(
    "sqlalchemy.url",
    sqlalchemy_url.render_as_string(
        hide_password=False
    ).replace("%", "%%")
)

# Reuse the logging configuration from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Migrations are authored explicitly because the app uses SQL, not ORM models.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
