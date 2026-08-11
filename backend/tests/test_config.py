"""Tests for application settings (`app/core/config.py`)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_list_splits_and_strips():
    settings = Settings(cors_origins="http://a.example, http://b.example ,, http://c.example")
    assert settings.cors_origins_list == [
        "http://a.example",
        "http://b.example",
        "http://c.example",
    ]


def test_cookie_flags_are_relaxed_in_development():
    settings = Settings(environment="development")
    assert settings.session_cookie_secure is False
    assert settings.session_cookie_samesite == "lax"


@pytest.mark.parametrize("environment", ["production", "staging", "test"])
def test_cookie_flags_are_strict_outside_development(environment):
    """`Secure` and `SameSite=None` must always flip on together: browsers
    reject a `SameSite=None` cookie that isn't also `Secure`, and the app's
    frontend/backend live on different hostnames in every non-development
    environment, so cross-site cookie delivery is required there."""

    settings = Settings(environment=environment)
    assert settings.session_cookie_secure is True
    assert settings.session_cookie_samesite == "none"


def test_database_ssl_mode_defaults_to_prefer():
    """ "prefer" matches the historical, unconfigured behavior against a
    non-SSL local/CI Postgres (connects in plaintext) while still using TLS
    when the server offers it."""

    assert Settings().database_ssl_mode == "prefer"


@pytest.mark.parametrize(
    "mode", ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
)
def test_database_ssl_mode_accepts_known_asyncpg_values(mode):
    assert Settings(database_ssl_mode=mode).database_ssl_mode == mode


def test_database_ssl_mode_rejects_unknown_values():
    """Rejects spellings asyncpg's `ssl` connect arg doesn't understand --
    notably the libpq-only `sslmode=require` query-string convention this
    setting exists to replace (see `app/db/session.py`)."""

    with pytest.raises(ValidationError):
        Settings(database_ssl_mode="sslmode=require")
