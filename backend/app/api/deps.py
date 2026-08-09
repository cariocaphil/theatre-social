"""Shared FastAPI dependencies for authenticated routes."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services import auth as auth_service


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db)) -> User:
    """Resolve the current User from the session cookie, or raise 401.

    Centralizes cookie-name lookup and session/expiry resolution (via
    `app/services/auth.get_user_by_session_token`) so every authenticated
    endpoint shares identical behavior instead of re-implementing it.
    """

    raw_token = request.cookies.get(get_settings().session_cookie_name)
    try:
        return await auth_service.get_user_by_session_token(session, raw_token)
    except auth_service.SessionInvalidError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc
