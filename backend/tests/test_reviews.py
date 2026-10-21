"""Tests for diary review publication and public production reviews."""

from datetime import date

import pytest

TODAY = date.today().isoformat()


async def _register(client, **overrides) -> dict:
    payload = {
        "username": "reviewer",
        "email": "reviewer@example.com",
        "password": "correct-password",
        **overrides,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _create_production(client, **overrides) -> dict:
    payload = {"title": "Reviewable Production", **overrides}
    response = await client.post("/api/v1/productions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _create_entry(client, production_id, **overrides) -> dict:
    payload = {"production_id": production_id, "watched_at": TODAY, **overrides}
    response = await client.post("/api/v1/diary", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_new_review_defaults_to_private(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(client, production["id"], review="Private thoughts.")

    assert body["review"] == "Private thoughts."
    assert body["published_at"] is None


@pytest.mark.asyncio
async def test_create_with_publish_review_atomic(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(
            client,
            production["id"],
            review="Public thoughts.",
            publish_review=True,
        )

        assert body["published_at"] is not None

        listed = await client.get(f"/api/v1/productions/{production['id']}/reviews")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["review"] == "Public thoughts."
        assert listed.json()["items"][0]["author_username"] == "reviewer"


@pytest.mark.asyncio
async def test_create_publish_without_review_rejected(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        response = await client.post(
            "/api/v1/diary",
            json={
                "production_id": production["id"],
                "watched_at": TODAY,
                "publish_review": True,
            },
        )

    assert response.status_code == 400
    assert "review" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_publish_and_idempotent_republish(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], review="To publish.")

        first = await client.post(f"/api/v1/diary/{entry['id']}/publish")
        assert first.status_code == 200
        published_at = first.json()["published_at"]
        assert published_at is not None

        second = await client.post(f"/api/v1/diary/{entry['id']}/publish")
        assert second.status_code == 200
        assert second.json()["published_at"] == published_at


@pytest.mark.asyncio
async def test_publish_rejects_empty_or_whitespace_review(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"])

        empty = await client.post(f"/api/v1/diary/{entry['id']}/publish")
        assert empty.status_code == 400

        await client.patch(f"/api/v1/diary/{entry['id']}", json={"review": "   "})
        whitespace = await client.post(f"/api/v1/diary/{entry['id']}/publish")
        assert whitespace.status_code == 400


@pytest.mark.asyncio
async def test_edit_published_preserves_published_at(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(
            client, production["id"], review="Original.", publish_review=True
        )
        published_at = entry["published_at"]

        patched = await client.patch(
            f"/api/v1/diary/{entry['id']}",
            json={"review": "Edited.", "rating": 4.0},
        )
        assert patched.status_code == 200
        assert patched.json()["review"] == "Edited."
        assert patched.json()["published_at"] == published_at


@pytest.mark.asyncio
async def test_cannot_clear_review_while_published(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(
            client, production["id"], review="Must keep.", publish_review=True
        )

        response = await client.patch(
            f"/api/v1/diary/{entry['id']}",
            json={"review": None},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unpublish_and_republish_new_timestamp(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], review="Cycle.", publish_review=True)
        first_ts = entry["published_at"]

        unpublished = await client.post(f"/api/v1/diary/{entry['id']}/unpublish")
        assert unpublished.status_code == 200
        assert unpublished.json()["published_at"] is None

        listed = await client.get(f"/api/v1/productions/{production['id']}/reviews")
        assert listed.json()["total"] == 0

        republished = await client.post(f"/api/v1/diary/{entry['id']}/publish")
        assert republished.status_code == 200
        assert republished.json()["published_at"] is not None
        assert republished.json()["published_at"] != first_ts


@pytest.mark.asyncio
async def test_publish_owner_only_returns_404_for_others(client_factory):
    async with client_factory() as owner_client:
        await _register(owner_client, username="owner", email="owner@example.com")
        production = await _create_production(owner_client)
        entry = await _create_entry(owner_client, production["id"], review="Mine.")

    async with client_factory() as other_client:
        await _register(other_client, username="other", email="other@example.com")
        response = await other_client.post(f"/api/v1/diary/{entry['id']}/publish")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_list_excludes_private_and_orders_deterministically(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)

        await _create_entry(client, production["id"], review="Private only.")
        first = await _create_entry(
            client, production["id"], review="First public.", publish_review=True
        )
        second = await _create_entry(
            client, production["id"], review="Second public.", publish_review=True
        )

        listed = await client.get(f"/api/v1/productions/{production['id']}/reviews")
        assert listed.status_code == 200
        body = listed.json()
        assert body["total"] == 2
        assert [item["review"] for item in body["items"]] == [
            "Second public.",
            "First public.",
        ]
        assert body["items"][0]["id"] == second["id"]
        assert body["items"][1]["id"] == first["id"]
        assert all("password" not in str(item).lower() for item in body["items"])


@pytest.mark.asyncio
async def test_public_reviews_pagination(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        for i in range(3):
            await _create_entry(
                client,
                production["id"],
                review=f"Review {i}",
                publish_review=True,
            )

        page = await client.get(
            f"/api/v1/productions/{production['id']}/reviews",
            params={"limit": 2, "offset": 0},
        )
        assert page.status_code == 200
        body = page.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["limit"] == 2
        assert body["offset"] == 0


@pytest.mark.asyncio
async def test_unauthenticated_publish_rejected(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], review="Secret.")

    async with client_factory() as anon:
        response = await anon.post(f"/api/v1/diary/{entry['id']}/publish")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_publish_review_flag_atomic(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], review="Draft.")

        patched = await client.patch(
            f"/api/v1/diary/{entry['id']}",
            json={"review": "Now public.", "publish_review": True},
        )
        assert patched.status_code == 200
        assert patched.json()["published_at"] is not None
        assert patched.json()["review"] == "Now public."
