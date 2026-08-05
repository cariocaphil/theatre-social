"""Health check route."""

import logging

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import HealthErrorResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthErrorResponse}},
    summary="Check API and database health",
)
async def health_check(session: AsyncSession = Depends(get_db)) -> Response:
    """Return service health, verifying the database with a lightweight `SELECT 1`."""

    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure here means "database unreachable"
        # Connection-time failures (DNS resolution, connection refused, timeouts, ...)
        # can surface as plain OSError subclasses rather than SQLAlchemyError, so we
        # deliberately catch broadly: every failure path must produce a clean 503.
        logger.warning("Database health check failed: %s", exc)
        error_body = HealthErrorResponse(detail="Database connection failed")
        return JSONResponse(status_code=503, content=error_body.model_dump())

    return JSONResponse(content=HealthResponse(status="ok", database="connected").model_dump())
