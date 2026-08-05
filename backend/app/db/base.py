"""Declarative base for SQLAlchemy models.

No application models exist yet. Future domain models should subclass
`Base` here so that Alembic autogenerate can discover them via
`Base.metadata`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
