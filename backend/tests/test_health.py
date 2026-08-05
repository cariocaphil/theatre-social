"""Tests for the /health endpoint."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


class _FakeWorkingSession:
    """Minimal stand-in for an AsyncSession whose `execute` always succeeds."""

    async def execute(self, *_args, **_kwargs):
        return None


class _FakeBrokenSession:
    """Minimal stand-in for an AsyncSession whose `execute` always fails."""

    async def execute(self, *_args, **_kwargs):
        raise OperationalError("could not connect to server", None, None)


class _FakeUnreachableHostSession:
    """Simulates a connection-time failure (e.g. DNS resolution), which
    asyncpg/SQLAlchemy can raise as a plain OSError subclass rather than a
    SQLAlchemyError."""

    async def execute(self, *_args, **_kwargs):
        raise OSError("Name or service not known")


@pytest.mark.asyncio
async def test_health_returns_ok_when_database_is_reachable(client_factory):
    async def _override() -> AsyncGenerator[_FakeWorkingSession, None]:
        yield _FakeWorkingSession()

    app.dependency_overrides[get_db] = _override

    async with client_factory() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


@pytest.mark.asyncio
async def test_health_returns_503_when_database_is_unreachable(client_factory):
    async def _override() -> AsyncGenerator[_FakeBrokenSession, None]:
        yield _FakeBrokenSession()

    app.dependency_overrides[get_db] = _override

    async with client_factory() as client:
        response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "disconnected"
    assert "detail" in body


@pytest.mark.asyncio
async def test_health_returns_503_when_host_is_unreachable(client_factory):
    async def _override() -> AsyncGenerator[_FakeUnreachableHostSession, None]:
        yield _FakeUnreachableHostSession()

    app.dependency_overrides[get_db] = _override

    async with client_factory() as client:
        response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "disconnected"
