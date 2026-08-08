"""create productions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-08

Creates the `productions` table: the single catalogue entity for v0.1.
`title` and `slug` are required (slug additionally unique); every other
business field is nullable. Work/Venue/Company/Director attribution is
stored as plain optional text columns on this table rather than as
separate normalized entities (see the root README for the reasoning).

Reversible: `downgrade()` drops every index this migration creates, then
the table itself.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "productions",
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
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("slug", sa.String(length=320), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("work_title", sa.String(length=300), nullable=True),
        sa.Column("creator_names", sa.String(length=500), nullable=True),
        sa.Column("company_name", sa.String(length=300), nullable=True),
        sa.Column("director_name", sa.String(length=300), nullable=True),
        sa.Column("venue_name", sa.String(length=300), nullable=True),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("premiere_date", sa.Date(), nullable=True),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_productions_slug"), "productions", ["slug"], unique=True)
    op.create_index(op.f("ix_productions_title"), "productions", ["title"], unique=False)
    op.create_index(op.f("ix_productions_work_title"), "productions", ["work_title"], unique=False)
    op.create_index(
        op.f("ix_productions_company_name"), "productions", ["company_name"], unique=False
    )
    op.create_index(
        op.f("ix_productions_director_name"), "productions", ["director_name"], unique=False
    )
    op.create_index(op.f("ix_productions_venue_name"), "productions", ["venue_name"], unique=False)
    op.create_index(op.f("ix_productions_city"), "productions", ["city"], unique=False)
    op.create_index(
        op.f("ix_productions_country_code"), "productions", ["country_code"], unique=False
    )
    op.create_index(
        op.f("ix_productions_premiere_date"), "productions", ["premiere_date"], unique=False
    )
    op.create_index(
        op.f("ix_productions_closing_date"), "productions", ["closing_date"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_productions_closing_date"), table_name="productions")
    op.drop_index(op.f("ix_productions_premiere_date"), table_name="productions")
    op.drop_index(op.f("ix_productions_country_code"), table_name="productions")
    op.drop_index(op.f("ix_productions_city"), table_name="productions")
    op.drop_index(op.f("ix_productions_venue_name"), table_name="productions")
    op.drop_index(op.f("ix_productions_director_name"), table_name="productions")
    op.drop_index(op.f("ix_productions_company_name"), table_name="productions")
    op.drop_index(op.f("ix_productions_work_title"), table_name="productions")
    op.drop_index(op.f("ix_productions_title"), table_name="productions")
    op.drop_index(op.f("ix_productions_slug"), table_name="productions")
    op.drop_table("productions")
