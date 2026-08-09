"""Business logic for registration, login, logout, and session resolution.

Plain async functions, consistent with `app/services/production.py` (no
repository/service class introduced). Session lookup is centralized here
(`get_user_by_session_token`) so `app/api/deps.py` and the auth routes never
duplicate the hash-then-query-then-check-expiry logic.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.session import Session as SessionModel
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin


class DuplicateUsernameError(Exception):
    """Raised when a username is already taken."""


class DuplicateEmailError(Exception):
    """Raised when an email is already registered."""


class InvalidCredentialsError(Exception):
    """Raised on login when the email/password combination is wrong.

    Deliberately carries no detail about *which* part was wrong, or
    whether the email exists at all -- callers must render a single
    generic "Invalid email or password" message.
    """


class SessionInvalidError(Exception):
    """Raised when a session cookie is missing, unrecognized, or expired."""


async def _username_taken(session: AsyncSession, username: str) -> bool:
    stmt = select(User.id).where(User.username == username)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _email_taken(session: AsyncSession, email: str) -> bool:
    stmt = select(User.id).where(User.email == email)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def register_user(session: AsyncSession, payload: UserCreate) -> User:
    """Create a User, rejecting duplicate usernames/emails.

    Pre-checks give a clear, specific error in the common case; the
    `IntegrityError` handler is the real source of truth for concurrency
    safety (two concurrent registrations could both pass the pre-checks
    before either commits).
    """

    if await _username_taken(session, payload.username):
        raise DuplicateUsernameError(payload.username)
    if await _email_taken(session, payload.email):
        raise DuplicateEmailError(payload.email)

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        detail = str(exc.orig).lower()
        if "username" in detail:
            raise DuplicateUsernameError(payload.username) from exc
        if "email" in detail:
            raise DuplicateEmailError(payload.email) from exc
        raise

    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, payload: UserLogin) -> User:
    """Verify email/password, raising `InvalidCredentialsError` on any mismatch.

    Never reveals whether the email exists: a nonexistent email and a wrong
    password both raise the same exception.
    """

    stmt = select(User).where(User.email == payload.email)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError()
    return user


async def create_session(
    session: AsyncSession, user: User, *, lifetime_days: int
) -> tuple[SessionModel, str]:
    """Create a new Session for `user`, returning it and the raw (unhashed) token.

    The raw token must only be used by the caller to set the cookie -- it
    is never itself persisted.
    """

    raw_token = generate_session_token()
    db_session = SessionModel(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=lifetime_days),
    )
    session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return db_session, raw_token


async def get_user_by_session_token(session: AsyncSession, raw_token: str | None) -> User:
    """Resolve a raw cookie token to its owning User, or raise `SessionInvalidError`.

    An expired Session is deleted opportunistically (no scheduled cleanup
    job -- see root README) and always treated as invalid.
    """

    if not raw_token:
        raise SessionInvalidError()

    stmt = (
        select(SessionModel)
        .options(joinedload(SessionModel.user))
        .where(SessionModel.token_hash == hash_session_token(raw_token))
    )
    db_session = (await session.execute(stmt)).unique().scalar_one_or_none()
    if db_session is None:
        raise SessionInvalidError()

    if db_session.expires_at <= datetime.now(UTC):
        await session.delete(db_session)
        await session.commit()
        raise SessionInvalidError()

    return db_session.user


async def delete_session_by_token(session: AsyncSession, raw_token: str | None) -> None:
    """Delete the Session matching `raw_token`, if any.

    Safe/idempotent by design: a missing, already-expired, or already-
    deleted token simply deletes zero rows. Used both for logout and to
    avoid accumulating redundant sessions when a valid cookie is presented
    again at login.
    """

    if not raw_token:
        return
    stmt = delete(SessionModel).where(SessionModel.token_hash == hash_session_token(raw_token))
    await session.execute(stmt)
    await session.commit()
