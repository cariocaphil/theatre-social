"""Authentication routes (`/api/v1/auth`): register, login, logout, me.

Session authentication via an opaque, high-entropy, HTTP-only cookie -- see
the root README's "Users & Authentication" section for the full flow.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_lifetime_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register(
    payload: UserCreate, response: Response, session: AsyncSession = Depends(get_db)
) -> UserRead:
    try:
        user = await auth_service.register_user(session, payload)
    except auth_service.DuplicateUsernameError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Username is already taken") from exc
    except auth_service.DuplicateEmailError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email is already registered") from exc

    settings = get_settings()
    _, raw_token = await auth_service.create_session(
        session, user, lifetime_days=settings.session_lifetime_days
    )
    _set_session_cookie(response, raw_token)
    return UserRead.model_validate(user)


@router.post("/login", response_model=UserRead, summary="Log in")
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> UserRead:
    try:
        user = await auth_service.authenticate_user(session, payload)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        ) from exc

    settings = get_settings()
    # Rotate: whatever session the incoming cookie referred to (valid,
    # expired, or missing -- deleting is a no-op either way) is dropped
    # before issuing a fresh one, so repeated logins don't accumulate
    # redundant sessions for the same browser.
    existing_token = request.cookies.get(settings.session_cookie_name)
    await auth_service.delete_session_by_token(session, existing_token)

    _, raw_token = await auth_service.create_session(
        session, user, lifetime_days=settings.session_lifetime_days
    )
    _set_session_cookie(response, raw_token)
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out")
async def logout(
    request: Request, response: Response, session: AsyncSession = Depends(get_db)
) -> None:
    """Delete the current Session (if any) and clear the cookie.

    Safe/idempotent: a missing or already-expired session simply results
    in zero rows deleted, and the cookie is cleared regardless.
    """

    raw_token = request.cookies.get(get_settings().session_cookie_name)
    await auth_service.delete_session_by_token(session, raw_token)
    _clear_session_cookie(response)


@router.get("/me", response_model=UserRead, summary="Get the current user")
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
