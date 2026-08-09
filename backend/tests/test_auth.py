"""Tests for authentication (`/api/v1/auth`): register, login, logout, me.

Like `test_productions.py`, these exercise the real database (see
`conftest.py`): a reachable PostgreSQL instance is required.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_session_token
from app.db.session import async_session_factory
from app.models.session import Session as SessionModel
from app.models.user import User

COOKIE_NAME = get_settings().session_cookie_name


async def _register(client, **overrides) -> dict:
    payload = {
        "username": "defaultuser",
        "email": "default@example.com",
        "password": "correct-password",
        **overrides,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _get_user_row(email: str) -> User:
    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)
        user = (await session.execute(stmt)).scalar_one()
        return user


async def _sessions_for_user(user_id: uuid.UUID) -> list[SessionModel]:
    async with async_session_factory() as session:
        stmt = select(SessionModel).where(SessionModel.user_id == user_id)
        return list((await session.execute(stmt)).scalars().all())


# --- Registration ------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success_returns_safe_user_and_sets_cookie(client_factory):
    async with client_factory() as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "correct-password",
            },
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password_hash" not in body
    assert "password" not in body
    assert uuid.UUID(body["id"])
    assert body["created_at"]
    assert body["updated_at"]
    assert COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_register_duplicate_username_rejected(client_factory):
    async with client_factory() as client:
        await _register(client, username="taken", email="first@example.com")
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "taken", "email": "second@example.com", "password": "another-pass"},
        )

    assert response.status_code == 409
    assert "password_hash" not in response.json()


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client_factory):
    async with client_factory() as client:
        await _register(client, username="firstuser", email="dupe@example.com")
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "seconduser",
                "email": "dupe@example.com",
                "password": "another-pass",
            },
        )

    assert response.status_code == 409
    assert "password_hash" not in response.json()


@pytest.mark.asyncio
async def test_register_normalizes_email(client_factory):
    async with client_factory() as client:
        body = await _register(client, email="  Mixed.Case@Example.COM  ")

    assert body["email"] == "mixed.case@example.com"
    user = await _get_user_row("mixed.case@example.com")
    assert user.email == "mixed.case@example.com"


@pytest.mark.asyncio
async def test_register_stores_argon2_password_hash_not_plaintext(client_factory):
    raw_password = "correct-password"
    async with client_factory() as client:
        await _register(client, email="hash-check@example.com", password=raw_password)

    user = await _get_user_row("hash-check@example.com")
    assert user.password_hash != raw_password
    assert raw_password not in user.password_hash
    assert user.password_hash.startswith("$argon2")


@pytest.mark.asyncio
async def test_register_creates_session_row(client_factory):
    async with client_factory() as client:
        body = await _register(client, email="session-check@example.com")

    sessions = await _sessions_for_user(uuid.UUID(body["id"]))
    assert len(sessions) == 1


# --- Session storage ----------------------------------------------------------


@pytest.mark.asyncio
async def test_session_row_stores_only_token_hash_never_raw_token(client_factory):
    async with client_factory() as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "tokencheck",
                "email": "tokencheck@example.com",
                "password": "correct-password",
            },
        )
        raw_token = response.cookies[COOKIE_NAME]
        user_id = uuid.UUID(response.json()["id"])

    sessions = await _sessions_for_user(user_id)
    assert len(sessions) == 1
    stored_session = sessions[0]

    # The persisted hash matches a hash of the raw token...
    assert stored_session.token_hash == hash_session_token(raw_token)
    # ...but the raw token itself is never what's stored.
    assert stored_session.token_hash != raw_token
    assert raw_token not in stored_session.token_hash


# --- Login ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success_returns_safe_user_and_sets_cookie(client_factory):
    async with client_factory() as client:
        await _register(client, email="login-success@example.com", password="correct-password")

    # A fresh client simulates a separate browser session (no leftover cookie).
    async with client_factory() as fresh_client:
        response = await fresh_client.post(
            "/api/v1/auth/login",
            json={"email": "login-success@example.com", "password": "correct-password"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "login-success@example.com"
    assert "password_hash" not in body
    assert COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_incorrect_password_rejected_generically(client_factory):
    async with client_factory() as client:
        await _register(client, email="wrongpass@example.com", password="correct-password")
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpass@example.com", "password": "totally-wrong"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_email_rejected_generically(client_factory):
    async with client_factory() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody-here@example.com", "password": "whatever-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_failure_messages_are_identical_for_both_cases(client_factory):
    async with client_factory() as client:
        await _register(client, email="exists@example.com", password="correct-password")
        wrong_password = await client.post(
            "/api/v1/auth/login", json={"email": "exists@example.com", "password": "nope"}
        )
        nonexistent = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "nope"}
        )

    assert wrong_password.json()["detail"] == nonexistent.json()["detail"]


@pytest.mark.asyncio
async def test_login_rotates_session_instead_of_accumulating(client_factory):
    async with client_factory() as client:
        register_body = await _register(
            client, email="rotate@example.com", password="correct-password"
        )
        user_id = uuid.UUID(register_body["id"])

        # The client still holds the cookie set at registration.
        await client.post(
            "/api/v1/auth/login",
            json={"email": "rotate@example.com", "password": "correct-password"},
        )

    sessions = await _sessions_for_user(user_id)
    assert len(sessions) == 1


# --- /me -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_authenticated_returns_current_user(client_factory):
    async with client_factory() as client:
        register_body = await _register(client, email="me-check@example.com")
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == register_body["id"]
    assert "password_hash" not in response.json()


@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401(client_factory):
    async with client_factory() as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_session_cookie_returns_401(client_factory):
    async with client_factory() as client:
        client.cookies.set(COOKIE_NAME, "not-a-real-token")
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_expired_session_returns_401(client_factory):
    from datetime import UTC, datetime, timedelta

    # Register to obtain a real, valid raw session token from the cookie jar.
    async with client_factory() as register_client:
        response = await register_client.post(
            "/api/v1/auth/register",
            json={
                "username": "expiredcheck",
                "email": "expired@example.com",
                "password": "correct-password",
            },
        )
        raw_token = response.cookies[COOKIE_NAME]

    # Force that Session to already be expired, simulating time passing.
    async with async_session_factory() as db_session:
        stmt = select(SessionModel).where(SessionModel.token_hash == hash_session_token(raw_token))
        stored_session = (await db_session.execute(stmt)).scalar_one()
        stored_session.expires_at = datetime.now(UTC) - timedelta(days=1)
        await db_session.commit()

    # A different client replays the (now-expired) cookie, like a browser would.
    async with client_factory() as client:
        client.cookies.set(COOKIE_NAME, raw_token)
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


# --- Logout ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_deletes_session_and_clears_cookie(client_factory):
    async with client_factory() as client:
        register_body = await _register(client, email="logout@example.com")
        user_id = uuid.UUID(register_body["id"])

        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204
        assert COOKIE_NAME not in client.cookies

        me_response = await client.get("/api/v1/auth/me")

    assert me_response.status_code == 401
    assert await _sessions_for_user(user_id) == []


@pytest.mark.asyncio
async def test_logout_is_safe_when_called_repeatedly(client_factory):
    async with client_factory() as client:
        await _register(client, email="repeat-logout@example.com")

        first = await client.post("/api/v1/auth/logout")
        second = await client.post("/api/v1/auth/logout")

    assert first.status_code == 204
    assert second.status_code == 204


@pytest.mark.asyncio
async def test_logout_without_any_session_is_safe(client_factory):
    async with client_factory() as client:
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
