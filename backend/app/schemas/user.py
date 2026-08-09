"""Pydantic schemas for User accounts and authentication payloads.

No `email-validator` dependency is introduced solely for `EmailStr`: a
lightweight regex sanity check (consistent with this project's preference
for small, dependency-free validation helpers -- see `app/core/slugify.py`)
is enough for an MVP that never sends email, and keeps `password_hash`
schema-invisible by construction (it simply never appears in any schema
below).
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,50}$")

_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 128


def _normalize_email(value: str) -> str:
    """Lowercase + strip, so lookups/uniqueness are effectively case-insensitive."""

    return value.strip().lower()


class UserCreate(BaseModel):
    """Payload for `POST /api/v1/auth/register`."""

    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        stripped = value.strip()
        if not _USERNAME_PATTERN.match(stripped):
            raise ValueError(
                "username must be 3-50 characters and contain only letters, digits, "
                "underscores, or hyphens"
            )
        return stripped

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email_before(cls, value: object) -> object:
        return _normalize_email(value) if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _validate_email_format(cls, value: str) -> str:
        if len(value) > 320 or not _EMAIL_PATTERN.match(value):
            raise ValueError("email must be a valid email address")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"password must be at least {_MIN_PASSWORD_LENGTH} characters")
        if len(value) > _MAX_PASSWORD_LENGTH:
            raise ValueError(f"password must be at most {_MAX_PASSWORD_LENGTH} characters")
        return value


class UserLogin(BaseModel):
    """Payload for `POST /api/v1/auth/login`."""

    email: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email_before(cls, value: object) -> object:
        return _normalize_email(value) if isinstance(value, str) else value


class UserRead(BaseModel):
    """Safe User representation. Never includes `password_hash`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
