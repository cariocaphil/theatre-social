"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Comma-separated list of allowed CORS origins, e.g. "http://localhost:3000".
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so environment parsing only happens once per process, while still
    being easy to override in tests via `app.dependency_overrides` or by
    clearing the cache (`get_settings.cache_clear()`).
    """

    return Settings()
