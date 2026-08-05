"""Shared pytest fixtures for backend tests."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


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
