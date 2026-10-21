"""Business logic for the diary (`DiaryEntry`).

Plain async functions, consistent with `app/services/production.py` and
`app/services/auth.py` (no repository/service class). Ownership is always
enforced here by filtering on `user_id` in the same query that looks the
row up -- callers never fetch-then-check, which would leave a window for
subtle bugs and doesn't match how `get_diary_entry` is written below.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.ratings import to_half_stars
from app.models.diary_entry import DiaryEntry
from app.schemas.diary import DiaryEntryCreate, DiaryEntryUpdate
from app.services.production import ProductionNotFoundError, get_production_by_id

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class DiaryEntryNotFoundError(Exception):
    """Raised when a diary entry cannot be found *for the requesting user*.

    Deliberately used both for a truly nonexistent id and for an id that
    belongs to another user: the diary API returns 404, not 403, for
    entries the current user doesn't own, consistent with this project's
    existing preference (see the auth system's generic login error) for
    not revealing information about resources a caller can't access.
    """


class ReviewPublishError(Exception):
    """Raised when publish rules are violated (empty review, etc.)."""


def _review_is_publishable(review: str | None) -> bool:
    return bool(review and review.strip())


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def create_diary_entry(
    session: AsyncSession, user_id: uuid.UUID, payload: DiaryEntryCreate
) -> DiaryEntry:
    # Raises ProductionNotFoundError (already an established, route-mapped
    # exception) if the referenced production doesn't exist.
    production = await get_production_by_id(session, payload.production_id)

    if payload.publish_review and not _review_is_publishable(payload.review):
        raise ReviewPublishError("Cannot publish without non-empty review text")

    entry = DiaryEntry(
        user_id=user_id,
        production_id=production.id,
        watched_at=payload.watched_at,
        rating=to_half_stars(payload.rating) if payload.rating is not None else None,
        review=payload.review,
        published_at=_utcnow() if payload.publish_review else None,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Defense in depth: the production existence check above is not
        # atomic with the insert, so a concurrent deletion between the two
        # would otherwise surface as a raw FK-violation IntegrityError.
        await session.rollback()
        raise ProductionNotFoundError(str(payload.production_id)) from exc

    return await get_diary_entry(session, entry.id, user_id)


async def get_diary_entry(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID
) -> DiaryEntry:
    stmt = (
        select(DiaryEntry)
        .options(joinedload(DiaryEntry.production))
        .where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
    )
    entry = (await session.execute(stmt)).unique().scalar_one_or_none()
    if entry is None:
        raise DiaryEntryNotFoundError(str(entry_id))
    return entry


async def list_diary_entries(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[DiaryEntry], int]:
    base_stmt = select(DiaryEntry).where(DiaryEntry.user_id == user_id)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    # Newest attendance first; `created_at` then `id` are deterministic
    # tiebreakers for entries sharing the same `watched_at` date, so
    # pagination never depends on PostgreSQL's implicit row order.
    page_stmt = (
        base_stmt.options(joinedload(DiaryEntry.production))
        .order_by(DiaryEntry.watched_at.desc(), DiaryEntry.created_at.desc(), DiaryEntry.id.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = (await session.execute(page_stmt)).unique().scalars().all()

    return list(entries), total


async def update_diary_entry(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID, payload: DiaryEntryUpdate
) -> DiaryEntry:
    entry = await get_diary_entry(session, entry_id, user_id)

    update_data = payload.model_dump(exclude_unset=True)
    publish_review = update_data.pop("publish_review", None)

    for field, value in update_data.items():
        if field == "rating":
            entry.rating = to_half_stars(value) if value is not None else None
        else:
            setattr(entry, field, value)

    resulting_review = entry.review
    will_be_published = entry.published_at is not None
    if publish_review is True:
        will_be_published = True
    elif publish_review is False:
        will_be_published = False

    if will_be_published and not _review_is_publishable(resulting_review):
        raise ReviewPublishError("Cannot leave a published review without non-empty review text")

    if publish_review is True:
        if entry.published_at is None:
            entry.published_at = _utcnow()
        # Idempotent: already published keeps original published_at.
    elif publish_review is False:
        entry.published_at = None

    await session.commit()
    return await get_diary_entry(session, entry_id, user_id)


async def delete_diary_entry(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    entry = await get_diary_entry(session, entry_id, user_id)
    await session.delete(entry)
    await session.commit()


async def publish_diary_entry(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID
) -> DiaryEntry:
    entry = await get_diary_entry(session, entry_id, user_id)
    if not _review_is_publishable(entry.review):
        raise ReviewPublishError("Cannot publish without non-empty review text")
    if entry.published_at is None:
        entry.published_at = _utcnow()
    await session.commit()
    return await get_diary_entry(session, entry_id, user_id)


async def unpublish_diary_entry(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID
) -> DiaryEntry:
    entry = await get_diary_entry(session, entry_id, user_id)
    entry.published_at = None
    await session.commit()
    return await get_diary_entry(session, entry_id, user_id)


async def list_published_reviews_for_production(
    session: AsyncSession,
    production_id: uuid.UUID,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[DiaryEntry], int]:
    # Ensure production exists (404) rather than returning an empty page for
    # a typo id — matches catalogue lookup conventions.
    await get_production_by_id(session, production_id)

    base_stmt = select(DiaryEntry).where(
        DiaryEntry.production_id == production_id,
        DiaryEntry.published_at.is_not(None),
    )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    page_stmt = (
        base_stmt.options(joinedload(DiaryEntry.user))
        .order_by(DiaryEntry.published_at.desc(), DiaryEntry.id.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = (await session.execute(page_stmt)).unique().scalars().all()
    return list(entries), total
