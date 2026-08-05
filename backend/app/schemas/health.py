"""Pydantic schemas for the /health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Returned when the API is running and the database is reachable."""

    status: str = "ok"
    database: str = "connected"


class HealthErrorResponse(BaseModel):
    """Returned when the database cannot be reached."""

    status: str = "error"
    database: str = "disconnected"
    detail: str
