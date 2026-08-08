"""SQLAlchemy model registry.

Importing this package registers every domain model on `Base.metadata`,
which both the app and Alembic's autogenerate rely on. `alembic/env.py`
imports this package before generating/running migrations.
"""

from app.models.production import Production

__all__ = ["Production"]
