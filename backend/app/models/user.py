"""User: a registered account.

Deliberately minimal for Phase 4 (see root README): only what's needed to
establish identity and authenticated ownership. No profile fields (avatar,
bio, ...) -- those are explicitly out of scope until a later phase actually
needs them.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UUIDAuditBase


class User(UUIDAuditBase):
    __tablename__ = "users"

    # 50 chars is a generous, conventional ceiling for a handle; unique +
    # indexed enforces "username unique at database level" and keeps
    # lookups fast.
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    # 320 is the RFC 5321 maximum email length. Always stored lowercased +
    # stripped (see `app/schemas/user.py`), so the unique constraint is
    # effectively case-insensitive.
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    # Argon2id hashes (see `app/core/security.py`) are ~100 chars but include
    # encoded parameters that can grow if they change; 255 leaves headroom
    # without ever being exposed through any API schema.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
