"""Pydantic schemas for the Production catalogue.

`ProductionBase` holds the optional metadata fields shared by every schema
so they are only declared once. `ProductionCreate` and `ProductionUpdate`
add the write-time fields/rules (`title`, `slug`) with different semantics
(required vs partial-update); `ProductionRead` and `ProductionSummary` add
the server-assigned fields for responses.
"""

import re
import unicodedata
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COUNTRY_CODE_PATTERN = re.compile(r"^[A-Za-z]{2}$")


def _normalize_blank(value: str | None) -> str | None:
    """Normalize a blank/whitespace-only optional string to `None`."""

    if value is None:
        return None
    stripped = unicodedata.normalize("NFC", value).strip()
    return stripped or None


def _validate_slug_format(value: str) -> str:
    if not _SLUG_PATTERN.match(value):
        raise ValueError(
            "slug must contain only lowercase letters, digits, and single hyphens "
            "between segments (e.g. 'hamlet-2')"
        )
    return value


class ProductionBase(BaseModel):
    """Optional business/metadata fields shared across Production schemas."""

    description: str | None = None
    work_title: str | None = None
    creator_names: str | None = None
    company_name: str | None = None
    director_name: str | None = None
    venue_name: str | None = None
    city: str | None = None
    country_code: str | None = None
    premiere_date: date | None = None
    closing_date: date | None = None

    @field_validator(
        "description",
        "work_title",
        "creator_names",
        "company_name",
        "director_name",
        "venue_name",
        "city",
        mode="before",
    )
    @classmethod
    def _blank_optional_to_none(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("country_code", mode="before")
    @classmethod
    def _normalize_country_code_case(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = _normalize_blank(value)
            return normalized.upper() if normalized is not None else None
        return value

    @field_validator("country_code")
    @classmethod
    def _validate_country_code_format(cls, value: str | None) -> str | None:
        if value is not None and not _COUNTRY_CODE_PATTERN.match(value):
            raise ValueError("country_code must be a two-letter ISO 3166-1 alpha-2 code")
        return value

    @model_validator(mode="after")
    def _validate_full_date_range(self) -> "ProductionBase":
        # Only meaningful when both dates are present (always true here for
        # ProductionCreate; ProductionUpdate overrides this check to only
        # apply it when both fields are explicitly part of the request).
        if (
            self.premiere_date is not None
            and self.closing_date is not None
            and self.closing_date < self.premiere_date
        ):
            raise ValueError("closing_date must be on or after premiere_date")
        return self


class ProductionCreate(ProductionBase):
    """Payload for `POST /api/v1/productions`."""

    title: str
    # Omit to have the backend generate a slug from `title`.
    slug: str | None = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str | None) -> str | None:
        return _validate_slug_format(value) if value is not None else value


class ProductionUpdate(BaseModel):
    """Payload for `PATCH /api/v1/productions/{id}`.

    Every field is optional so requests can be partial. Route/service code
    must use `model_dump(exclude_unset=True)` so omitted fields are left
    untouched, while an explicit `null` clears a nullable field. `title`
    and `slug` are business-required, so an explicit `null` for either is
    rejected rather than silently ignored.
    """

    title: str | None = None
    slug: str | None = None
    description: str | None = None
    work_title: str | None = None
    creator_names: str | None = None
    company_name: str | None = None
    director_name: str | None = None
    venue_name: str | None = None
    city: str | None = None
    country_code: str | None = None
    premiere_date: date | None = None
    closing_date: date | None = None

    @field_validator(
        "description",
        "work_title",
        "creator_names",
        "company_name",
        "director_name",
        "venue_name",
        "city",
        mode="before",
    )
    @classmethod
    def _blank_optional_to_none(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("country_code", mode="before")
    @classmethod
    def _normalize_country_code_case(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = _normalize_blank(value)
            return normalized.upper() if normalized is not None else None
        return value

    @field_validator("country_code")
    @classmethod
    def _validate_country_code_format(cls, value: str | None) -> str | None:
        if value is not None and not _COUNTRY_CODE_PATTERN.match(value):
            raise ValueError("country_code must be a two-letter ISO 3166-1 alpha-2 code")
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, value: object) -> object:
        return _normalize_blank(value) if isinstance(value, str) else value

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str | None) -> str | None:
        return _validate_slug_format(value) if value is not None else value

    @model_validator(mode="after")
    def _validate_partial_update(self) -> "ProductionUpdate":
        fields_set = self.model_fields_set

        if "title" in fields_set and self.title is None:
            raise ValueError("title cannot be cleared; omit it instead of setting it to null")
        if "slug" in fields_set and self.slug is None:
            raise ValueError("slug cannot be cleared; omit it instead of setting it to null")

        # A full date-range check requires knowing both the pre-existing and
        # the incoming values; here we can only reject the case that is
        # unambiguously invalid from the payload alone (both supplied in
        # this request). The service layer re-validates the merged record
        # before committing, to catch cases like "only closing_date is
        # being updated to a date before the existing premiere_date".
        if (
            "premiere_date" in fields_set
            and "closing_date" in fields_set
            and self.premiere_date is not None
            and self.closing_date is not None
            and self.closing_date < self.premiere_date
        ):
            raise ValueError("closing_date must be on or after premiere_date")

        return self


class ProductionRead(ProductionBase):
    """Full Production representation, used for single-item responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    created_at: datetime
    updated_at: datetime


class ProductionSummary(BaseModel):
    """Lighter Production representation used in list responses.

    Omits `description`, which the catalogue list view does not display
    (see the frontend `/productions` page), to keep list payloads smaller.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    work_title: str | None = None
    creator_names: str | None = None
    company_name: str | None = None
    director_name: str | None = None
    venue_name: str | None = None
    city: str | None = None
    country_code: str | None = None
    premiere_date: date | None = None
    closing_date: date | None = None
    created_at: datetime
    updated_at: datetime
