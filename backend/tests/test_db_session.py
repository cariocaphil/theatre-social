"""Tests for engine construction (`app/db/session.py`), focused on the SSL wiring.

These don't open a real connection -- they assert that `create_engine()` asks
SQLAlchemy for the right `connect_args`, since that's the part that's easy to
get subtly wrong (see the module's docstring/comments for why a `sslmode=...`
query parameter on `database_url` would not work).
"""

from app.core import config
from app.db import session as db_session


def test_create_engine_passes_ssl_mode_as_connect_arg(monkeypatch):
    captured: dict = {}

    def _fake_create_async_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return "fake-engine"

    monkeypatch.setattr(db_session, "create_async_engine", _fake_create_async_engine)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: config.Settings(
            database_url="postgresql+asyncpg://u:p@example.invalid/db",
            database_ssl_mode="require",
        ),
    )
    # `db_session.get_settings` is the name actually referenced inside
    # `create_engine()` (imported directly into the module's namespace).
    monkeypatch.setattr(db_session, "get_settings", config.get_settings)

    result = db_session.create_engine()

    assert result == "fake-engine"
    assert captured["kwargs"]["connect_args"] == {"ssl": "require"}


def test_create_engine_defaults_to_prefer(monkeypatch):
    captured: dict = {}

    def _fake_create_async_engine(url, **kwargs):
        captured["kwargs"] = kwargs
        return "fake-engine"

    monkeypatch.setattr(db_session, "create_async_engine", _fake_create_async_engine)
    monkeypatch.setattr(
        db_session,
        "get_settings",
        lambda: config.Settings(database_url="postgresql+asyncpg://u:p@example.invalid/db"),
    )

    db_session.create_engine()

    assert captured["kwargs"]["connect_args"] == {"ssl": "prefer"}
