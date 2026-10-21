"""add diary entry published_at

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21

Adds nullable timezone-aware `published_at` on `diary_entries` for review-text
publication (PR 11). Existing rows stay unpublished (`NULL`); no backfill.

Partial index backs public list queries filtered to published rows ordered by
`published_at` descending for a given production.

Reversible: drops the index then the column.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diary_entries",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_diary_entries_production_id_published_at",
        "diary_entries",
        ["production_id", "published_at"],
        unique=False,
        postgresql_where=sa.text("published_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_diary_entries_production_id_published_at",
        table_name="diary_entries",
        postgresql_where=sa.text("published_at IS NOT NULL"),
    )
    op.drop_column("diary_entries", "published_at")
