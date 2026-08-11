"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    # `ssl` (not `sslmode`) is the only TLS knob asyncpg's `connect()` accepts;
    # SQLAlchemy's asyncpg dialect forwards query-string params from
    # `database_url` straight through as connect() kwargs, so a `?sslmode=...`
    # query parameter would raise a TypeError instead of configuring TLS. See
    # `Settings.database_ssl_mode` for the environment-driven value.
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
        connect_args={"ssl": settings.database_ssl_mode},
    )


engine: AsyncEngine = create_engine()

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an `AsyncSession` for a single request."""

    async with async_session_factory() as session:
        yield session
