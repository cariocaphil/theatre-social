"""Pydantic schemas for the diary (`DiaryEntry`).

`rating` is always 0.5-5.0 at this layer (and in `DiaryEntry`, at the
persistence layer it's a 1-10 half-star integer -- see
`app/core/ratings.py`); conversion happens only here and in the service
layer, never in routes or the frontend.

There is no separate `DiaryEntrySummary`: unlike `ProductionSummary` (which
exists to omit the heavier `description` field from list responses),
`DiaryEntry` has no field worth omitting from the diary list -- `review` is
already length-bounded and is exactly what the diary list needs to render.
Introducing a second, near-identical schema here would be speculative.
"""

import unicodedata
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.ratings import MAX_RATING, MIN_RATING, from_half_stars
from app.models.diary_entry import DiaryEntry
from app.schemas.production import ProductionSummary

# Chosen to comfortably fit a genuine review while bounding payload size;
# documented here as the single source of truth for the limit.
MAX_REVIEW_LENGTH = 4000

_HALF_STAR_TOLERANCE = 1e-9


def _normalize_blank(value: str | None) -> str | None:
    """Normalize a blank/whitespace-only optional string to `None`."""

    if value is None:
        return None
    stripped = unicodedata.normalize("NFC", value).strip()
    return stripped or None


def _validate_rating_value(value: float | None) -> float | None:
    if value is None:
        return None
    if value < MIN_RATING or value > MAX_RATING:
        raise ValueError(f"rating must be between {MIN_RATING} and {MAX_RATING}")
    doubled = value * 2
    if abs(doubled - round(doubled)) > _HALF_STAR_TOLERANCE:
        raise ValueError("rating must be in 0.5 increments (0.5, 1.0, 1.5, ..., 5.0)")
    return value


def _validate_review_length(value: str | None) -> str | None:
    if value is not None and len(value) > MAX_REVIEW_LENGTH:
        raise ValueError(f"review must be at most {MAX_REVIEW_LENGTH} characters")
    return value


def _validate_not_future(value: date) -> date:
    if value > date.today():
        raise ValueError("watched_at cannot be in the future")
    return value


class DiaryEntryCreate(BaseModel):
    """Payload for `POST /api/v1/diary`.

    `user_id` is deliberately absent: ownership always comes from the
    authenticated session (`get_current_user`), never from the request
    body. `production_id` is required and immutable after creation --
    logging the wrong production means creating a new, correct entry, not
    reassigning an existing one.
    """

    production_id: uuid.UUID
    watched_at: date
    rating: float | None = None
    review: str | None = None

    @field_validator("watched_at")
    @classmethod
    def _validate_watched_at(cls, value: date) -> date:
        return _validate_not_future(value)

    @field_validator("rating")
    @classmethod
    def _validate_rating(cls, value: float | None) -> float | None:
        return _validate_rating_value(value)

    @field_validator("review", mode="before")
    @classmethod
    def _normalize_review(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("review")
    @classmethod
    def _validate_review(cls, value: str | None) -> str | None:
        return _validate_review_length(value)


class DiaryEntryUpdate(BaseModel):
    """Payload for `PATCH /api/v1/diary/{entry_id}`.

    Partial update semantics matching `ProductionUpdate`: omitted fields are
    left untouched (`model_dump(exclude_unset=True)` in the service layer),
    while an explicit `null` clears `rating`/`review`. `watched_at` is
    required business data, so an explicit `null` for it is rejected --
    same rule as `title`/`slug` on `ProductionUpdate`. There is no
    `production_id` field at all: the production a log refers to is
    immutable after creation.
    """

    watched_at: date | None = None
    rating: float | None = None
    review: str | None = None

    @field_validator("watched_at")
    @classmethod
    def _validate_watched_at(cls, value: date | None) -> date | None:
        return _validate_not_future(value) if value is not None else value

    @field_validator("rating")
    @classmethod
    def _validate_rating(cls, value: float | None) -> float | None:
        return _validate_rating_value(value)

    @field_validator("review", mode="before")
    @classmethod
    def _normalize_review(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("review")
    @classmethod
    def _validate_review(cls, value: str | None) -> str | None:
        return _validate_review_length(value)

    @model_validator(mode="after")
    def _validate_partial_update(self) -> "DiaryEntryUpdate":
        if "watched_at" in self.model_fields_set and self.watched_at is None:
            raise ValueError("watched_at cannot be cleared; omit it instead of setting it to null")
        return self


class DiaryEntryRead(BaseModel):
    """Full DiaryEntry representation, including an embedded Production summary.

    Built via `from_model` rather than plain `model_validate(entry, from_attributes=True)`:
    `rating` needs the half-star -> public-scale conversion, and `production`
    needs the already-loaded relationship converted to `ProductionSummary`
    (see `app/services/diary.py`, which always eager-loads it to avoid N+1
    queries when listing).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    production_id: uuid.UUID
    production: ProductionSummary
    watched_at: date
    rating: float | None
    review: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, entry: DiaryEntry) -> "DiaryEntryRead":
        return cls(
            id=entry.id,
            production_id=entry.production_id,
            production=ProductionSummary.model_validate(entry.production),
            watched_at=entry.watched_at,
            rating=from_half_stars(entry.rating),
            review=entry.review,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
