"""Declarative base and shared model mixins for SQLAlchemy models.

Phase 1 shipped no domain models, so this only contained a bare
`DeclarativeBase`. `UUIDAuditBase` is added here as the single place that
defines the UUID primary key and `created_at`/`updated_at` timestamp
behavior; domain models should subclass `UUIDAuditBase` (not `Base`
directly) so that logic is never duplicated per-model.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDAuditBase(Base):
    """Abstract base providing a UUID primary key and audit timestamps.

    - `id` is generated application-side (`uuid.uuid4`) so it is available
      before the row is flushed/committed.
    - `created_at` / `updated_at` use `server_default=func.now()` (and
      `onupdate=func.now()` for the latter) so the database is the source
      of truth for timestamps, consistent across direct SQL and the ORM.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
