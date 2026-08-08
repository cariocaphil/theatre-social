"""Minimal, dependency-free slug generation.

Only used for Production slug auto-generation, so a small self-contained
implementation is preferred over adding a dedicated slugify package for a
single use case.
"""

import re
import unicodedata

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Convert `value` into a lowercase, hyphen-separated, URL-safe slug.

    Accented/diacritic characters are transliterated to their closest ASCII
    equivalent (e.g. "ü" -> "u") where possible; characters with no ASCII
    equivalent are dropped. Any remaining run of non-alphanumeric characters
    becomes a single hyphen, and leading/trailing hyphens are stripped.
    """

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return _NON_SLUG_CHARS.sub("-", ascii_only.lower()).strip("-")
