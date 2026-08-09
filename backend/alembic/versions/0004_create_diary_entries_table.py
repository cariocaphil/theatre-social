"""create diary entries table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-09

Creates the `diary_entries` table for Phase 5 (Production Logging & Diary):
a User's record of one attendance of a Production. `user_id` and
`production_id` are both required and never unique together -- the same
user may log the same production multiple times (repeat attendance), so no
`(user_id, production_id)` uniqueness is enforced.

Foreign-key delete behavior is intentionally asymmetric:
- `user_id -> users.id` is `ON DELETE CASCADE`: deleting a User deletes
  their diary history with it (same convention as `sessions.user_id`).
- `production_id -> productions.id` is `ON DELETE RESTRICT`: a Production
  with diary history must not be silently hard-deleted out of the
  catalogue. Deleting such a Production is left as an explicit decision
  this phase does not implement (no archival/soft-delete).

`rating` is a half-star integer (1-10; see `app/core/ratings.py`), guarded
by a `CHECK` constraint at the database level rather than relying solely on
Pydantic validation for an invariant this simple to protect directly.

The composite index on `(user_id, watched_at, created_at)` backs the
primary diary query (current user's entries, newest attendance first, with
`created_at` as the documented tiebreaker) without needing a separate
single-column `user_id` index on top of it; `production_id` also has its
own index, consistent with indexing foreign-key columns.

Reversible: `downgrade()` drops every index and constraint this migration
creates, then the table itself.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "diary_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("production_id", sa.UUID(), nullable=False),
        sa.Column("watched_at", sa.Date(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("review", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["production_id"], ["productions.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 10)",
            name="ck_diary_entries_rating_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diary_entries_user_id"), "diary_entries", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_diary_entries_production_id"), "diary_entries", ["production_id"], unique=False
    )
    op.create_index(
        "ix_diary_entries_user_id_watched_at_created_at",
        "diary_entries",
        ["user_id", "watched_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_diary_entries_user_id_watched_at_created_at", table_name="diary_entries")
    op.drop_index(op.f("ix_diary_entries_production_id"), table_name="diary_entries")
    op.drop_index(op.f("ix_diary_entries_user_id"), table_name="diary_entries")
    op.drop_table("diary_entries")
