"""Alembic environment configuration for the async SQLAlchemy engine.

Uses the same `Settings.database_url` as the FastAPI app, and the same
`Base.metadata` so that future models automatically become visible to
`alembic revision --autogenerate`.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401 - registers models on Base.metadata for autogenerate
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", get_settings().database_url)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates raw SQL)."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations using an async engine, via `run_sync` for the sync API Alembic expects."""

    # Alembic builds its own engine here rather than reusing
    # `app.db.session.create_engine()`, so the same SSL connect_args must be
    # applied explicitly -- see that module for why `ssl=...` (not a
    # `sslmode=...` query param) is the correct mechanism.
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"ssl": get_settings().database_ssl_mode},
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
