"""Star-rating conversion between the public API scale and DB storage.

Public API/frontend: 0.5-5.0 in 0.5 increments (Letterboxd-style). Database/
model: a `SMALLINT` half-star count, 1-10. Storing the half-star integer
(rather than a `float`/`NUMERIC`) avoids IEEE-754 rounding entirely and
reflects that a rating is really a discrete 10-value domain, not an
arbitrary decimal. Centralized here so schemas/services/tests all convert
the same way instead of duplicating the `* 2` / `/ 2` arithmetic.
"""

MIN_RATING = 0.5
MAX_RATING = 5.0
MIN_HALF_STARS = 1
MAX_HALF_STARS = 10


def to_half_stars(rating: float) -> int:
    """Convert a public 0.5-5.0 rating to its stored half-star integer (1-10).

    Callers must validate the input is on a valid half-star increment first
    (see `app/schemas/diary.py`); this only performs the arithmetic.
    """

    return round(rating * 2)


def from_half_stars(value: int | None) -> float | None:
    """Convert a stored half-star integer (1-10) back to a public 0.5-5.0 rating."""

    if value is None:
        return None
    return value / 2
