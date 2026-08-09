"""Session: a server-side record backing the `ts_session` HTTP-only cookie.

The browser only ever holds an opaque, high-entropy token (see
`app/core/security.py`); this table stores a SHA-256 hash of that token,
never the raw value, so a database dump alone cannot be replayed as a
valid session cookie.

Does not inherit `UUIDAuditBase`: sessions are immutable once created (only
ever looked up or deleted, never edited), so there is no `updated_at` --
just `id` and `created_at`, following the same UUID/timestamp conventions
as `UUIDAuditBase` individually rather than pulling in a field that would
never change.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # ON DELETE CASCADE: deleting a User must clean up their Sessions, at the
    # database level so it holds even for direct SQL/manual deletes.
    user_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # A hex-encoded SHA-256 digest is always exactly 64 characters.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Not eager by default: callers that need the User must opt in via
    # `.options(joinedload(Session.user))` (see `app/api/deps.py`), so the
    # eager-load strategy is visible at each call site instead of being an
    # implicit, easy-to-miss relationship default.
    user: Mapped["User"] = relationship()
