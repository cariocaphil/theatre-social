"""DiaryEntry: a User's record of attending/watching a Production.

Production is the thing that was seen; DiaryEntry is *this user's* record of
one specific attendance of it. A user may log the same Production multiple
times (e.g. seeing the same run twice, or a revival years later) -- each
attendance is its own row, so there is deliberately no unique constraint on
`(user_id, production_id)`.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import UUIDAuditBase

if TYPE_CHECKING:
    from app.models.production import Production


class DiaryEntry(UUIDAuditBase):
    __tablename__ = "diary_entries"
    __table_args__ = (
        # Backs the primary diary query (current user's entries, newest
        # attendance first, with `created_at` as the documented tiebreaker
        # for same-day entries) via a single composite index rather than
        # several overlapping single-column ones.
        Index(
            "ix_diary_entries_user_id_watched_at_created_at", "user_id", "watched_at", "created_at"
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 10)",
            name="ck_diary_entries_rating_range",
        ),
    )

    # ON DELETE CASCADE: deleting a User account deletes their diary history
    # with it (same convention as Session -> User, see app/models/session.py).
    user_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # ON DELETE RESTRICT: a Production with diary history must not be
    # silently hard-deleted out from under users' logs. Deleting such a
    # Production is an explicit product/data-management decision, not a
    # side effect of a catalogue cleanup -- this phase does not implement
    # that decision (no archival/soft-delete), it only protects against it.
    production_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("productions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Attendance date, not a timestamp: the MVP only cares about *which day*
    # the user attended, not the time. Required (every log needs a date).
    watched_at: Mapped[date] = mapped_column(Date, nullable=False)

    # Half-star units, 1-10 (see app/core/ratings.py for the 0.5-5.0 <->
    # 1-10 conversion). Optional: logging a Production should not require
    # rating it.
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Plain text only; length is enforced in the Pydantic schema
    # (app/schemas/diary.py), consistent with how Production.description
    # (also unconstrained `Text`) relies on the schema layer, not a DB
    # column length, for its limit.
    review: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Not eager by default, same rationale as Session.user: callers that
    # need the Production must opt in via `.options(joinedload(...))` (see
    # app/services/diary.py), so the eager-load strategy stays visible at
    # each call site.
    production: Mapped["Production"] = relationship()
