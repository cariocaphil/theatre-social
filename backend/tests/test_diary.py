"""Tests for the diary (`/api/v1/diary`): logging attendance of a Production.

Like `test_productions.py` / `test_auth.py`, these exercise the real
database (see `conftest.py`): a reachable PostgreSQL instance is required.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.schemas.diary import MAX_REVIEW_LENGTH

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


async def _register(client, **overrides) -> dict:
    payload = {
        "username": "diaryuser",
        "email": "diaryuser@example.com",
        "password": "correct-password",
        **overrides,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _create_production(client, **overrides) -> dict:
    payload = {"title": "Default Test Production", **overrides}
    response = await client.post("/api/v1/productions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _create_entry_response(client, production_id, **overrides):
    payload = {"production_id": production_id, "watched_at": TODAY, **overrides}
    return await client.post("/api/v1/diary", json=payload)


async def _create_entry(client, production_id, **overrides) -> dict:
    response = await _create_entry_response(client, production_id, **overrides)
    assert response.status_code == 201, response.text
    return response.json()


# --- Creation ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_minimal_diary_entry(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client, title="Hamlet")
        body = await _create_entry(client, production["id"], watched_at="2026-03-14")

    assert uuid.UUID(body["id"])
    assert body["production_id"] == production["id"]
    assert body["production"]["title"] == "Hamlet"
    assert body["watched_at"] == "2026-03-14"
    assert body["rating"] is None
    assert body["review"] is None
    assert body["created_at"]
    assert body["updated_at"]


@pytest.mark.asyncio
async def test_create_entry_with_rating(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(client, production["id"], rating=4.5)

    assert body["rating"] == 4.5
    assert body["review"] is None


@pytest.mark.asyncio
async def test_create_entry_with_review(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(client, production["id"], review="A remarkable production.")

    assert body["review"] == "A remarkable production."
    assert body["rating"] is None


@pytest.mark.asyncio
async def test_create_entry_with_rating_and_review(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(
            client, production["id"], rating=3.5, review="Solid staging, uneven pacing."
        )

    assert body["rating"] == 3.5
    assert body["review"] == "Solid staging, uneven pacing."


@pytest.mark.asyncio
@pytest.mark.parametrize("rating", [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
async def test_rating_round_trips_across_all_half_star_values(client_factory, rating):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(client, production["id"], rating=rating)

    assert body["rating"] == rating


@pytest.mark.asyncio
async def test_reject_future_watched_at(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        response = await _create_entry_response(client, production["id"], watched_at=TOMORROW)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_rating_below_half_star(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        response = await _create_entry_response(client, production["id"], rating=0.0)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_rating_above_five_stars(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        response = await _create_entry_response(client, production["id"], rating=5.5)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_rating_not_aligned_to_half_star_increment(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        response = await _create_entry_response(client, production["id"], rating=3.3)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_review_above_max_length(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        response = await _create_entry_response(
            client, production["id"], review="x" * (MAX_REVIEW_LENGTH + 1)
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_review_at_max_length_is_accepted(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        body = await _create_entry(client, production["id"], review="x" * MAX_REVIEW_LENGTH)

    assert len(body["review"]) == MAX_REVIEW_LENGTH


@pytest.mark.asyncio
async def test_reject_nonexistent_production(client_factory):
    async with client_factory() as client:
        await _register(client)
        response = await _create_entry_response(client, str(uuid.uuid4()))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_unauthenticated_creation(client_factory):
    async with client_factory() as owner_client:
        await _register(owner_client)
        production = await _create_production(owner_client)

    async with client_factory() as anon_client:
        response = await _create_entry_response(anon_client, production["id"])

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_id_cannot_be_spoofed_through_request_body(client_factory):
    async with client_factory() as client_a, client_factory() as client_b:
        user_a = await _register(client_a, username="usera", email="usera@example.com")
        await _register(client_b, username="userb", email="userb@example.com")
        production = await _create_production(client_a)

        entry = await _create_entry(client_a, production["id"], user_id=user_a["id"])

        # The spoofed field is silently ignored: ownership still comes from
        # client_a's own session, so client_b (a different authenticated
        # user) cannot see the entry.
        forbidden = await client_b.get(f"/api/v1/diary/{entry['id']}")

    assert forbidden.status_code == 404


# --- Multiple attendance --------------------------------------------------------


@pytest.mark.asyncio
async def test_same_user_can_log_same_production_twice(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client, title="Hamlet")

        first = await _create_entry(client, production["id"], watched_at="2026-03-14")
        second = await _create_entry(client, production["id"], watched_at="2026-08-08")

        listing = await client.get("/api/v1/diary")

    assert first["id"] != second["id"]
    body = listing.json()
    assert body["total"] == 2
    ids = {item["id"] for item in body["items"]}
    assert ids == {first["id"], second["id"]}


@pytest.mark.asyncio
async def test_logging_again_does_not_overwrite_the_first_entry(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)

        first = await _create_entry(
            client, production["id"], watched_at="2026-03-14", rating=3.0, review="First time."
        )
        await _create_entry(
            client, production["id"], watched_at="2026-08-08", rating=5.0, review="Even better!"
        )

        refetched_first = await client.get(f"/api/v1/diary/{first['id']}")

    body = refetched_first.json()
    assert body["watched_at"] == "2026-03-14"
    assert body["rating"] == 3.0
    assert body["review"] == "First time."


# --- Listing ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diary_contains_only_current_users_entries(client_factory):
    async with client_factory() as client_a, client_factory() as client_b:
        await _register(client_a, username="usera", email="usera@example.com")
        await _register(client_b, username="userb", email="userb@example.com")
        production = await _create_production(client_a)

        await _create_entry(client_a, production["id"])
        await _create_entry(client_b, production["id"])

        listing_a = await client_a.get("/api/v1/diary")
        listing_b = await client_b.get("/api/v1/diary")

    assert listing_a.json()["total"] == 1
    assert listing_b.json()["total"] == 1


@pytest.mark.asyncio
async def test_entries_ordered_by_watched_at_desc(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)

        await _create_entry(client, production["id"], watched_at="2026-01-01")
        await _create_entry(client, production["id"], watched_at="2026-06-15")
        await _create_entry(client, production["id"], watched_at="2026-03-01")

        listing = await client.get("/api/v1/diary")

    dates = [item["watched_at"] for item in listing.json()["items"]]
    assert dates == ["2026-06-15", "2026-03-01", "2026-01-01"]


@pytest.mark.asyncio
async def test_same_date_entries_use_deterministic_secondary_ordering(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)

        first = await _create_entry(client, production["id"], watched_at="2026-05-01", review="A")
        second = await _create_entry(client, production["id"], watched_at="2026-05-01", review="B")

        listing = await client.get("/api/v1/diary")

    ids = [item["id"] for item in listing.json()["items"]]
    # Both share `watched_at`; the more recently created entry sorts first.
    assert ids == [second["id"], first["id"]]


@pytest.mark.asyncio
async def test_listing_includes_production_summary(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(
            client, title="Hamlet", venue_name="Schaubuehne am Lehniner Platz", city="Berlin"
        )
        await _create_entry(client, production["id"])

        listing = await client.get("/api/v1/diary")

    item = listing.json()["items"][0]
    assert item["production"]["title"] == "Hamlet"
    assert item["production"]["venue_name"] == "Schaubuehne am Lehniner Platz"
    assert item["production"]["city"] == "Berlin"


@pytest.mark.asyncio
async def test_diary_pagination_total_limit_offset(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        for i in range(5):
            await _create_entry(client, production["id"], watched_at=f"2026-01-{i + 1:02d}")

        first_page = await client.get("/api/v1/diary", params={"limit": 2, "offset": 0})
        second_page = await client.get("/api/v1/diary", params={"limit": 2, "offset": 2})

    assert first_page.json()["total"] == 5
    assert len(first_page.json()["items"]) == 2
    assert first_page.json()["limit"] == 2
    assert first_page.json()["offset"] == 0

    assert len(second_page.json()["items"]) == 2
    first_ids = {item["id"] for item in first_page.json()["items"]}
    second_ids = {item["id"] for item in second_page.json()["items"]}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_list_diary(client_factory):
    async with client_factory() as client:
        response = await client.get("/api/v1/diary")

    assert response.status_code == 401


# --- Retrieval -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_own_diary_entry(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], rating=4.0)

        response = await client.get(f"/api/v1/diary/{entry['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == entry["id"]


@pytest.mark.asyncio
async def test_cannot_retrieve_another_users_diary_entry(client_factory):
    async with client_factory() as client_a, client_factory() as client_b:
        await _register(client_a, username="usera", email="usera@example.com")
        await _register(client_b, username="userb", email="userb@example.com")
        production = await _create_production(client_a)
        entry = await _create_entry(client_a, production["id"])

        response = await client_b.get(f"/api/v1/diary/{entry['id']}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retrieve_nonexistent_diary_entry_returns_404(client_factory):
    async with client_factory() as client:
        await _register(client)
        response = await client.get(f"/api/v1/diary/{uuid.uuid4()}")

    assert response.status_code == 404


# --- Update ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_watched_at(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], watched_at="2026-01-01")

        response = await client.patch(
            f"/api/v1/diary/{entry['id']}", json={"watched_at": "2026-02-02"}
        )

    assert response.status_code == 200
    assert response.json()["watched_at"] == "2026-02-02"


@pytest.mark.asyncio
async def test_reject_update_to_future_date(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"])

        response = await client.patch(f"/api/v1/diary/{entry['id']}", json={"watched_at": TOMORROW})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_rating(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], rating=2.0)

        response = await client.patch(f"/api/v1/diary/{entry['id']}", json={"rating": 4.5})

    assert response.status_code == 200
    assert response.json()["rating"] == 4.5


@pytest.mark.asyncio
async def test_clear_rating(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], rating=3.0)

        response = await client.patch(f"/api/v1/diary/{entry['id']}", json={"rating": None})

    assert response.status_code == 200
    assert response.json()["rating"] is None


@pytest.mark.asyncio
async def test_update_review(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], review="Original review.")

        response = await client.patch(
            f"/api/v1/diary/{entry['id']}", json={"review": "Updated review."}
        )

    assert response.status_code == 200
    assert response.json()["review"] == "Updated review."


@pytest.mark.asyncio
async def test_clear_review(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"], review="Original review.")

        response = await client.patch(f"/api/v1/diary/{entry['id']}", json={"review": None})

    assert response.status_code == 200
    assert response.json()["review"] is None


@pytest.mark.asyncio
async def test_reject_invalid_rating_on_update(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"])

        response = await client.patch(f"/api/v1/diary/{entry['id']}", json={"rating": 3.3})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_clearing_watched_at(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"])

        response = await client.patch(f"/api/v1/diary/{entry['id']}", json={"watched_at": None})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_cannot_update_another_users_entry(client_factory):
    async with client_factory() as client_a, client_factory() as client_b:
        await _register(client_a, username="usera", email="usera@example.com")
        await _register(client_b, username="userb", email="userb@example.com")
        production = await _create_production(client_a)
        entry = await _create_entry(client_a, production["id"], review="Original.")

        response = await client_b.patch(
            f"/api/v1/diary/{entry['id']}", json={"review": "Hijacked!"}
        )
        unchanged = await client_a.get(f"/api/v1/diary/{entry['id']}")

    assert response.status_code == 404
    assert unchanged.json()["review"] == "Original."


# --- Delete ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_own_entry(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"])

        response = await client.delete(f"/api/v1/diary/{entry['id']}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_deleted_entry_no_longer_returned(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        entry = await _create_entry(client, production["id"])

        await client.delete(f"/api/v1/diary/{entry['id']}")
        get_response = await client.get(f"/api/v1/diary/{entry['id']}")
        listing = await client.get("/api/v1/diary")

    assert get_response.status_code == 404
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_user_cannot_delete_another_users_entry(client_factory):
    async with client_factory() as client_a, client_factory() as client_b:
        await _register(client_a, username="usera", email="usera@example.com")
        await _register(client_b, username="userb", email="userb@example.com")
        production = await _create_production(client_a)
        entry = await _create_entry(client_a, production["id"])

        response = await client_b.delete(f"/api/v1/diary/{entry['id']}")
        still_there = await client_a.get(f"/api/v1/diary/{entry['id']}")

    assert response.status_code == 404
    assert still_there.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_cannot_delete(client_factory):
    async with client_factory() as owner_client:
        await _register(owner_client)
        production = await _create_production(owner_client)
        entry = await _create_entry(owner_client, production["id"])

    async with client_factory() as anon_client:
        response = await anon_client.delete(f"/api/v1/diary/{entry['id']}")

    assert response.status_code == 401


# --- Foreign-key protection -------------------------------------------------------


@pytest.mark.asyncio
async def test_production_with_diary_history_cannot_be_deleted(client_factory):
    async with client_factory() as client:
        await _register(client)
        production = await _create_production(client)
        await _create_entry(client, production["id"])

        response = await client.delete(f"/api/v1/productions/{production['id']}")

    assert response.status_code == 409
