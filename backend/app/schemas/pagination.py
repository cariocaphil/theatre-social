"""Generic pagination envelope.

Phase 1 had no paginated endpoints yet, so this is introduced now as a
small, reusable generic rather than a Production-specific response shape,
so future list endpoints (if any) can reuse it without duplicating the
`items` / `total` / `limit` / `offset` shape.
"""

from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
