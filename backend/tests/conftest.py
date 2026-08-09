"""Shared pytest fixtures for backend tests."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine, get_db
from app.main import app
from app.models import DiaryEntry, Production, Session, User  # noqa: F401 (registers metadata)


@pytest.fixture
def client_factory():
    """Return a factory for building an `AsyncClient` against the FastAPI app.

    Kept as a factory (rather than a single fixture) so individual tests can
    install their own `get_db` dependency override before the client is
    constructed.
    """

    def _make_client() -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")

    return _make_client


@pytest.fixture(autouse=True)
def _reset_overrides() -> AsyncGenerator[None, None]:
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_schema() -> AsyncGenerator[None, None]:
    """Ensure the schema exists before Production tests run.

    Production tests exercise real SQL (ILIKE, uniqueness, ordering), so
    they run against a real PostgreSQL database rather than a mocked
    session, consistent with the project's async-SQLAlchemy-only
    conventions. This requires a reachable database at `DATABASE_URL` (see
    README: "Backend tests requiring a database").
    """

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables() -> AsyncGenerator[None, None]:
    """Truncate every domain table before each test, for isolation.

    Listed together in one statement so Postgres handles the `sessions` ->
    `users` and `diary_entries` -> `users`/`productions` foreign keys
    correctly regardless of order.
    """

    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE productions, sessions, users, diary_entries"))
    yield
