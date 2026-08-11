"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# The exact string values asyncpg's `ssl` connect arg understands (mirrors
# libpq's sslmode names). See `app/db/session.py` for why this can't just be
# a `sslmode=...` query parameter on `database_url` instead.
DatabaseSSLMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]


class Settings(BaseSettings):
    """Runtime settings for the backend service.

    Values are read from environment variables (and, for local development,
    from a `.env` file in the `backend/` directory). See `backend/.env.example`
    for the full list of supported variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "theatre-social-backend"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://theatre_social:theatre_social_dev_password@postgres:5432/theatre_social"
    # How the database connection negotiates TLS. "prefer" (the default)
    # matches the historical, unconfigured behavior against local/CI Postgres
    # (no SSL, connects in plaintext). Azure Database for PostgreSQL Flexible
    # Server requires TLS, so production sets this to "require" via an Azure
    # application setting -- no code change needed between environments.
    database_ssl_mode: DatabaseSSLMode = "prefer"

    # Comma-separated list of allowed CORS origins, e.g. "http://localhost:3000".
    cors_origins: str = "http://localhost:3000"

    # Name of the HTTP-only cookie holding the opaque session token.
    session_cookie_name: str = "ts_session"
    # How long a session (and its cookie) stays valid before `/auth/me` and
    # other authenticated requests start treating it as expired.
    session_lifetime_days: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def session_cookie_secure(self) -> bool:
        """Whether the session cookie should require HTTPS.

        Derived from `environment` (already the project's convention for
        environment-specific behavior) rather than a separate flag: `False`
        for local HTTP development, `True` everywhere else.
        """

        return self.environment != "development"

    @property
    def session_cookie_samesite(self) -> Literal["lax", "none"]:
        """Whether the session cookie is sent on cross-site requests.

        Locally, the frontend (`localhost:3000`) and backend (`localhost:8000`)
        share the same registrable domain ("localhost"), so `Lax` already
        works fine for the browser's cross-origin `fetch(..., {credentials:
        "include"})` calls. In production the frontend and backend are on
        different Azure hostnames, which browsers treat as cross-*site* (not
        just cross-origin): `Lax` cookies are withheld from those requests
        entirely, silently breaking auth. `None` fixes that, and requires
        `Secure`, which `session_cookie_secure` already guarantees together
        with this (both flip on `environment != "development"`).
        """

        return "lax" if self.environment == "development" else "none"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so environment parsing only happens once per process, while still
    being easy to override in tests via `app.dependency_overrides` or by
    clearing the cache (`get_settings.cache_clear()`).
    """

    return Settings()
