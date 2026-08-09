"""Business logic for the Production catalogue.

Kept as plain async functions (not a repository/service class) since Phase 1
established no persistence-layer abstraction; this keeps `app/api/routes/
productions.py` thin without introducing a new architectural pattern for a
single entity.
"""

import uuid
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.slugify import slugify
from app.models.production import Production
from app.schemas.production import ProductionCreate, ProductionUpdate

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class ProductionNotFoundError(Exception):
    """Raised when a Production cannot be found by ID or slug."""


class DuplicateSlugError(Exception):
    """Raised when an explicit slug collides with an existing Production."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"A production with slug '{slug}' already exists")


class InvalidDateRangeError(Exception):
    """Raised when closing_date would end up earlier than premiere_date."""


class ProductionDeletionRestrictedError(Exception):
    """Raised when a Production can't be deleted because other rows reference it.

    Deliberately doesn't name a specific referencing table: this module
    stays decoupled from e.g. `diary_entries` (Phase 5's `ON DELETE
    RESTRICT` foreign key), it just translates *any* such database-level
    restriction into a controlled API error instead of a raw
    `IntegrityError`.
    """


def _check_date_range(premiere_date: date | None, closing_date: date | None) -> None:
    if premiere_date is not None and closing_date is not None and closing_date < premiere_date:
        raise InvalidDateRangeError("closing_date must be on or after premiere_date")


async def _slug_exists(
    session: AsyncSession, slug: str, *, exclude_id: uuid.UUID | None = None
) -> bool:
    stmt = select(Production.id).where(Production.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Production.id != exclude_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _generate_unique_slug(session: AsyncSession, title: str) -> str:
    """Generate a slug from `title`, appending a deterministic numeric
    suffix (`-2`, `-3`, ...) on collision. Never uses random hashes.
    """

    base = slugify(title) or "production"
    candidate = base
    suffix = 2
    while await _slug_exists(session, candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _apply_search_and_filters(
    stmt: Select,
    *,
    search: str | None,
    work_title: str | None,
    company_name: str | None,
    director_name: str | None,
    venue_name: str | None,
    city: str | None,
    country_code: str | None,
    from_date: date | None,
    to_date: date | None,
) -> Select:
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Production.title.ilike(pattern),
                Production.work_title.ilike(pattern),
                Production.creator_names.ilike(pattern),
                Production.company_name.ilike(pattern),
                Production.director_name.ilike(pattern),
                Production.venue_name.ilike(pattern),
                Production.city.ilike(pattern),
            )
        )
    if work_title:
        stmt = stmt.where(Production.work_title.ilike(f"%{work_title}%"))
    if company_name:
        stmt = stmt.where(Production.company_name.ilike(f"%{company_name}%"))
    if director_name:
        stmt = stmt.where(Production.director_name.ilike(f"%{director_name}%"))
    if venue_name:
        stmt = stmt.where(Production.venue_name.ilike(f"%{venue_name}%"))
    if city:
        stmt = stmt.where(Production.city.ilike(f"%{city}%"))
    if country_code:
        stmt = stmt.where(func.upper(Production.country_code) == country_code.upper())

    # Date-range overlap semantics (see README "Date filtering" section for
    # the documented, user-facing behavior):
    #   - Filter only applies when from_date and/or to_date is supplied.
    #   - A Production with no premiere_date is excluded whenever a date
    #     filter is supplied (we can't know whether it overlaps).
    #   - A Production with no closing_date is treated as still running
    #     (open-ended), so it always satisfies the from_date bound.
    #   - Only from_date: matches if the run has not already closed before
    #     from_date.
    #   - Only to_date: matches if the run started on or before to_date.
    #   - Both supplied: both conditions apply (standard interval overlap).
    if from_date is not None or to_date is not None:
        stmt = stmt.where(Production.premiere_date.is_not(None))
        if from_date is not None:
            stmt = stmt.where(
                or_(Production.closing_date.is_(None), Production.closing_date >= from_date)
            )
        if to_date is not None:
            stmt = stmt.where(Production.premiere_date <= to_date)

    return stmt


async def list_productions(
    session: AsyncSession,
    *,
    search: str | None = None,
    work_title: str | None = None,
    company_name: str | None = None,
    director_name: str | None = None,
    venue_name: str | None = None,
    city: str | None = None,
    country_code: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[Production], int]:
    base_stmt = _apply_search_and_filters(
        select(Production),
        search=search,
        work_title=work_title,
        company_name=company_name,
        director_name=director_name,
        venue_name=venue_name,
        city=city,
        country_code=country_code,
        from_date=from_date,
        to_date=to_date,
    )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    # Deterministic ordering: title ASC, then id ASC as a tiebreaker so rows
    # with equal titles still sort consistently across pages/requests.
    page_stmt = base_stmt.order_by(Production.title.asc(), Production.id.asc())
    page_stmt = page_stmt.limit(limit).offset(offset)
    productions = (await session.execute(page_stmt)).scalars().all()

    return list(productions), total


async def get_production_by_id(session: AsyncSession, production_id: uuid.UUID) -> Production:
    production = await session.get(Production, production_id)
    if production is None:
        raise ProductionNotFoundError(str(production_id))
    return production


async def get_production_by_slug(session: AsyncSession, slug: str) -> Production:
    stmt = select(Production).where(Production.slug == slug)
    production = (await session.execute(stmt)).scalar_one_or_none()
    if production is None:
        raise ProductionNotFoundError(slug)
    return production


async def create_production(session: AsyncSession, payload: ProductionCreate) -> Production:
    _check_date_range(payload.premiere_date, payload.closing_date)

    if payload.slug is not None:
        if await _slug_exists(session, payload.slug):
            raise DuplicateSlugError(payload.slug)
        slug = payload.slug
    else:
        slug = await _generate_unique_slug(session, payload.title)

    production = Production(
        title=payload.title,
        slug=slug,
        description=payload.description,
        work_title=payload.work_title,
        creator_names=payload.creator_names,
        company_name=payload.company_name,
        director_name=payload.director_name,
        venue_name=payload.venue_name,
        city=payload.city,
        country_code=payload.country_code,
        premiere_date=payload.premiere_date,
        closing_date=payload.closing_date,
    )
    session.add(production)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Final concurrency safety net: two concurrent requests could both
        # pass the `_slug_exists` check above before either commits. The
        # database's unique constraint is the actual source of truth.
        await session.rollback()
        raise DuplicateSlugError(slug) from exc

    await session.refresh(production)
    return production


async def update_production(
    session: AsyncSession, production_id: uuid.UUID, payload: ProductionUpdate
) -> Production:
    production = await get_production_by_id(session, production_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "slug" in update_data:
        new_slug = update_data["slug"]
        if new_slug != production.slug and await _slug_exists(
            session, new_slug, exclude_id=production.id
        ):
            raise DuplicateSlugError(new_slug)

    for field, value in update_data.items():
        setattr(production, field, value)

    # Re-validate the *merged* record: the payload alone can't tell us
    # whether e.g. a new closing_date conflicts with an untouched,
    # already-persisted premiere_date.
    _check_date_range(production.premiere_date, production.closing_date)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DuplicateSlugError(update_data.get("slug", production.slug)) from exc

    await session.refresh(production)
    return production


async def delete_production(session: AsyncSession, production_id: uuid.UUID) -> None:
    production = await get_production_by_id(session, production_id)
    await session.delete(production)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ProductionDeletionRestrictedError(str(production_id)) from exc
