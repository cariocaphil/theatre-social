"""initial (no application tables yet)

Revision ID: 0001
Revises:
Create Date: 2026-08-05

This migration intentionally contains no application tables. It establishes
the Alembic baseline (`Base.metadata`, async engine wiring) so that future
`alembic revision --autogenerate -m "..."` runs have a starting point once
domain models are added.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
