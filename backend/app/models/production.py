"""Production: the primary catalogue entity for v0.1.

A Production represents a staging of a show that users will eventually be
able to log, review, rate, or discuss (a specific run of "Hamlet" at a
specific theatre, a stand-up set, an improv night, ...).

Work and Venue are intentionally *not* separate entities yet: `work_title`
and `venue_name` (along with `creator_names`, `company_name`,
`director_name`) are plain optional text metadata on the Production. See
the root README for the reasoning.
"""

from datetime import date

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import UUIDAuditBase


class Production(UUIDAuditBase):
    __tablename__ = "productions"

    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    # Unique + indexed: unique enforces the business rule at the database
    # level, index keeps slug-based lookups (GET /productions/slug/{slug})
    # fast. SQLAlchemy's `unique=True` already implies a unique constraint
    # that Postgres backs with an index, but `index=True` is kept explicit
    # here to make the requirement visible in the model itself.
    slug: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional plain-text metadata (see module docstring: no Work/Venue/
    # Company/Person tables in v0.1).
    work_title: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    creator_names: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    director_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    venue_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)

    premiere_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
